"""
Document Ingestor — orchestrates the full ingestion pipeline.

Pipeline: Extract → Chunk → Embed → Store

Usage:
    ingestor = DocumentIngestor()
    result = ingestor.ingest_file("path/to/document.pdf")
    # or
    result = ingestor.ingest_file("path/to/doc.md", source_type="obsidian", vault_path="/vault")
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Literal

from .chunker import Chunker
from .embeddings import EmbeddingManager
from .extractors import get_extractor_for_file, get_extractor_for_type
from .extractors.web import WebExtractor
from .models import (
    DocumentChunk,
    IngestRequest,
    IngestResponse,
    IngestedDocument,
)
from .vectorstore import VectorStore


class DocumentIngestor:
    """
    Main ingestion orchestrator.

    Coordinates extractors, chunker, embedding manager, and vector store
    to process documents into searchable knowledge.
    """

    def __init__(
        self,
        chunker: Chunker | None = None,
        embedding_manager: EmbeddingManager | None = None,
        vector_store: VectorStore | None = None,
    ):
        self.chunker = chunker or Chunker()
        self.embeddings = embedding_manager or EmbeddingManager()
        self.vector_store = vector_store or VectorStore()

    def ingest_file(
        self,
        file_path: str | Path,
        source_type: Literal["pdf", "docx", "csv", "image", "web", "text", "markdown", "obsidian"] | None = None,
        title: str | None = None,
        vault_path: str | None = None,
        auto_index: bool = True,
    ) -> IngestResponse:
        """
        Ingest a single file through the full pipeline.

        Args:
            file_path: Path to the file
            source_type: Override auto-detection
            title: Optional document title
            vault_path: If from Obsidian vault, the vault root path
            auto_index: Whether to add to vector store immediately

        Returns:
            IngestResponse with status and chunk count
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return IngestResponse(
                document_id="",
                source_path=str(file_path),
                status="failed",
                chunks_created=0,
                error=f"File not found: {file_path}",
            )

        # Determine source type
        if not source_type:
            ext = file_path.suffix.lower()
            type_map = {
                ".pdf": "pdf",
                ".docx": "docx",
                ".csv": "csv",
                ".txt": "text",
                ".md": "obsidian" if vault_path else "markdown",
                ".markdown": "obsidian" if vault_path else "markdown",
                ".html": "web",
                ".htm": "web",
                ".png": "image",
                ".jpg": "image",
                ".jpeg": "image",
                ".gif": "image",
            }
            source_type = type_map.get(ext, "text")  # type: ignore

        source_type = source_type or "text"

        # Create document metadata
        doc_meta = IngestedDocument(
            source_path=str(file_path.resolve()),
            source_type=source_type,
            title=title or file_path.stem,
            filename=file_path.name,
            file_size_bytes=file_path.stat().st_size,
            checksum=self._checksum(file_path),
            vault_path=vault_path,
            status="extracting",
        )

        try:
            # Step 1: Extract
            doc_meta.status = "extracting"
            extractor = get_extractor_for_type(source_type) or get_extractor_for_file(str(file_path))
            if not extractor:
                return IngestResponse(
                    document_id=doc_meta.id,
                    source_path=str(file_path),
                    status="failed",
                    chunks_created=0,
                    error=f"No extractor found for {source_type}",
                )

            extracted = extractor.extract(str(file_path))
            if extracted.has_error:
                doc_meta.status = "failed"
                doc_meta.error_message = extracted.error
                return IngestResponse(
                    document_id=doc_meta.id,
                    source_path=str(file_path),
                    status="failed",
                    chunks_created=0,
                    error=extracted.error,
                )

            # Update metadata from extraction
            if extracted.title:
                doc_meta.title = extracted.title
            doc_meta.total_words = extracted.total_words
            doc_meta.obsidian_tags = extracted.metadata.get("obsidian_tags", [])
            doc_meta.frontmatter = extracted.metadata.get("frontmatter", {})

            # Step 2: Chunk
            doc_meta.status = "chunking"
            chunks = self.chunker.chunk_document(extracted, doc_meta)
            doc_meta.total_chunks = len(chunks)

            if not chunks:
                return IngestResponse(
                    document_id=doc_meta.id,
                    source_path=str(file_path),
                    status="failed",
                    chunks_created=0,
                    error="No chunks generated from document",
                )

            # Step 3: Embed
            doc_meta.status = "embedding"
            embed_start = time.perf_counter()
            chunks = self.embeddings.embed_chunks(chunks)
            embed_time = (time.perf_counter() - embed_start) * 1000

            # Step 4: Store
            if auto_index:
                doc_meta.status = "indexed"
                added = self.vector_store.add_chunks(chunks, doc_meta)
            else:
                added = len(chunks)

            return IngestResponse(
                document_id=doc_meta.id,
                source_path=str(file_path),
                status="indexed" if auto_index else "chunked",
                chunks_created=added,
                embedding_time_ms=embed_time,
            )

        except Exception as e:
            doc_meta.status = "failed"
            doc_meta.error_message = str(e)
            return IngestResponse(
                document_id=doc_meta.id,
                source_path=str(file_path),
                status="failed",
                chunks_created=0,
                error=str(e),
            )

    def ingest_web(
        self,
        url: str,
        title: str | None = None,
        auto_index: bool = True,
    ) -> IngestResponse:
        """
        Ingest a web page by URL.

        Args:
            url: The web page URL
            title: Optional override title
            auto_index: Whether to add to vector store

        Returns:
            IngestResponse with status
        """
        doc_meta = IngestedDocument(
            source_path=url,
            source_type="web",
            title=title or url,
            filename=url.split("/")[-1] or "webpage",
            file_size_bytes=0,
            checksum=hashlib.sha256(url.encode()).hexdigest()[:16],
            status="extracting",
        )

        try:
            extractor = WebExtractor()
            extracted = extractor.extract_from_url(url)

            if extracted.has_error:
                return IngestResponse(
                    document_id=doc_meta.id,
                    source_path=url,
                    status="failed",
                    chunks_created=0,
                    error=extracted.error,
                )

            if extracted.title:
                doc_meta.title = extracted.title
            doc_meta.total_words = extracted.total_words

            # Chunk, embed, store
            chunks = self.chunker.chunk_document(extracted, doc_meta)
            doc_meta.total_chunks = len(chunks)

            if not chunks:
                return IngestResponse(
                    document_id=doc_meta.id,
                    source_path=url,
                    status="failed",
                    chunks_created=0,
                    error="No content extracted from web page",
                )

            embed_start = time.perf_counter()
            chunks = self.embeddings.embed_chunks(chunks)
            embed_time = (time.perf_counter() - embed_start) * 1000

            if auto_index:
                self.vector_store.add_chunks(chunks, doc_meta)

            return IngestResponse(
                document_id=doc_meta.id,
                source_path=url,
                status="indexed" if auto_index else "chunked",
                chunks_created=len(chunks),
                embedding_time_ms=embed_time,
            )

        except Exception as e:
            return IngestResponse(
                document_id=doc_meta.id,
                source_path=url,
                status="failed",
                chunks_created=0,
                error=str(e),
            )

    def ingest_request(self, request: IngestRequest) -> IngestResponse:
        """Ingest from an IngestRequest (for API endpoints)."""
        if request.source_path.startswith(("http://", "https://")):
            return self.ingest_web(
                url=request.source_path,
                title=request.title,
                auto_index=request.auto_index,
            )
        return self.ingest_file(
            file_path=request.source_path,
            source_type=request.source_type,
            title=request.title,
            vault_path=request.vault_sync if isinstance(request.vault_sync, str) else None,
            auto_index=request.auto_index,
        )

    @staticmethod
    def _checksum(file_path: Path) -> str:
        """Calculate SHA-256 checksum for deduplication."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def get_info(self) -> dict:
        """Get ingestion pipeline status."""
        return {
            "embedding": self.embeddings.get_info(),
            "vector_store": {
                "collection": self.vector_store.collection_name,
                "total_chunks": self.vector_store.count(),
            },
            "chunker": {
                "chunk_size": self.chunker.chunk_size,
                "chunk_overlap": self.chunker.chunk_overlap,
                "strategy": self.chunker.strategy,
            },
        }

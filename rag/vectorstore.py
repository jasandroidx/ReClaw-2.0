"""
Vector Store — ChromaDB integration for semantic search.

Uses ChromaDB in embedded mode (no separate service needed).
Stores chunks with full citation metadata for retrieval.

Collections:
  - "reclaw_knowledge": main collection for all ingested documents
  - "reclaw_vault": Obsidian vault documents only

Metadata filtering supports:
  - source_type: pdf, docx, csv, image, web, text, markdown, obsidian
  - vault_path: specific vault folder
  - tags: Obsidian tags
  - document_id: chunks from a specific document
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from .models import CitationRef, DocumentChunk, IngestedDocument, RetrievalResult


class VectorStore:
    """
    ChromaDB-based vector store for document chunks.

    Embedded mode — no Docker container needed.
    Data persisted to disk at data/rag_chroma/.
    """

    DEFAULT_COLLECTION = "reclaw_knowledge"
    VAULT_COLLECTION = "reclaw_vault"
    PERSIST_DIR = "data/rag_chroma"

    def __init__(
        self,
        persist_dir: str | Path | None = None,
        collection_name: str | None = None,
        embedding_dim: int = 384,
    ):
        self.persist_dir = Path(persist_dir or self.PERSIST_DIR)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name or self.DEFAULT_COLLECTION
        self.embedding_dim = embedding_dim
        self._client: chromadb.Client | None = None
        self._collection: chromadb.Collection | None = None

    @property
    def client(self) -> chromadb.Client:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        return self._client

    @property
    def collection(self) -> chromadb.Collection:
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add_chunks(
        self,
        chunks: list[DocumentChunk],
        doc_meta: IngestedDocument,
    ) -> int:
        """
        Add chunks to the vector store.

        Args:
            chunks: Chunks with embeddings already computed
            doc_meta: Parent document metadata

        Returns:
            Number of chunks added
        """
        if not chunks:
            return 0

        # Filter to chunks with embeddings
        valid_chunks = [c for c in chunks if c.has_embedding]
        if not valid_chunks:
            return 0

        ids = [c.id for c in valid_chunks]
        embeddings = [c.embedding for c in valid_chunks]  # type: ignore
        documents = [c.text for c in valid_chunks]
        metadatas = [
            self._chunk_to_metadata(c, doc_meta)
            for c in valid_chunks
        ]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return len(valid_chunks)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        source_types: list[str] | None = None,
        vault_only: bool = False,
        min_score: float = 0.0,
        document_id: str | None = None,
    ) -> list[RetrievalResult]:
        """
        Semantic search with optional metadata filters.

        Args:
            query_embedding: The embedded query vector
            top_k: Number of results
            source_types: Filter by document types
            vault_only: Only search Obsidian vault docs
            min_score: Minimum similarity score (0-1, using cosine distance)
            document_id: Filter to specific document

        Returns:
            List of RetrievalResult with chunks and scores
        """
        where_filter = self._build_where_filter(
            source_types=source_types,
            vault_only=vault_only,
            document_id=document_id,
        )

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 2,  # oversample for filtering
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"],
        )

        retrieval_results: list[RetrievalResult] = []

        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, (doc_id, doc_text, meta, distance) in enumerate(zip(ids, docs, metas, distances)):
            # Convert cosine distance to similarity score (0-1)
            # Chroma cosine distance: 0 = identical, 2 = opposite
            score = 1 - (distance / 2) if distance is not None else 0.0

            if score < min_score:
                continue

            chunk = self._metadata_to_chunk(doc_id, doc_text, meta)
            retrieval_results.append(RetrievalResult(
                chunk=chunk,
                score=score,
                rank=i,
                query="",  # filled by caller
            ))

            if len(retrieval_results) >= top_k:
                break

        # Re-rank by score
        retrieval_results.sort(key=lambda r: r.score, reverse=True)
        for i, r in enumerate(retrieval_results):
            r.rank = i + 1

        return retrieval_results

    def delete_document(self, document_id: str) -> int:
        """Delete all chunks for a given document."""
        result = self.collection.delete(
            where={"document_id": document_id}
        )
        return result or 0

    def get_document_chunks(self, document_id: str) -> list[DocumentChunk]:
        """Get all chunks for a document."""
        results = self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
        )
        chunks: list[DocumentChunk] = []
        ids = results.get("ids", [])
        docs = results.get("documents", [])
        metas = results.get("metadatas", [])
        for doc_id, doc_text, meta in zip(ids, docs, metas):
            chunks.append(self._metadata_to_chunk(doc_id, doc_text, meta))
        return chunks

    def list_documents(
        self,
        source_type: str | None = None,
    ) -> list[dict]:
        """List unique documents in the store."""
        where_filter = {"source_type": source_type} if source_type else None
        results = self.collection.get(
            where=where_filter,
            include=["metadatas"],
        )

        # Group by document_id
        docs: dict[str, dict] = {}
        for meta in results.get("metadatas", []):
            doc_id = meta.get("document_id")
            if doc_id and doc_id not in docs:
                docs[doc_id] = {
                    "document_id": doc_id,
                    "source_path": meta.get("source_path"),
                    "source_type": meta.get("source_type"),
                    "title": meta.get("title"),
                    "filename": meta.get("filename"),
                    "vault_path": meta.get("vault_path"),
                    "ingested_at": meta.get("ingested_at"),
                }

        return list(docs.values())

    def count(self) -> int:
        """Total number of chunks in the collection."""
        return self.collection.count()

    def reset(self) -> None:
        """⚠️ Delete all data in the collection."""
        self.client.delete_collection(self.collection_name)
        self._collection = None

    def _build_where_filter(
        self,
        source_types: list[str] | None = None,
        vault_only: bool = False,
        document_id: str | None = None,
    ) -> dict | None:
        """Build ChromaDB where filter from search parameters."""
        filters: list[dict] = []

        if document_id:
            filters.append({"document_id": document_id})

        if source_types:
            if len(source_types) == 1:
                filters.append({"source_type": source_types[0]})
            else:
                filters.append({"source_type": {"$in": source_types}})

        if vault_only:
            filters.append({"vault_path": {"$ne": None}})

        if not filters:
            return None
        if len(filters) == 1:
            return filters[0]
        return {"$and": filters}

    @staticmethod
    def _sanitize_chroma_value(value: Any) -> str | int | float | bool:
        """Chroma metadata accepts only str, int, float, or bool — never None or nested objects."""
        if value is None:
            return ""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, (list, dict)):
            return json.dumps(value)
        return str(value)

    @staticmethod
    def _chunk_to_metadata(chunk: DocumentChunk, doc_meta: IngestedDocument) -> dict:
        """Convert chunk + doc metadata to ChromaDB metadata dict."""
        c = chunk.citation
        raw = {
            "document_id": doc_meta.id,
            "chunk_index": chunk.chunk_index,
            "source_path": c.source_path,
            "source_type": c.source_type,
            "filename": doc_meta.filename,
            "title": doc_meta.title or doc_meta.filename,
            "page_number": c.page_number,
            "line_start": c.line_start,
            "line_end": c.line_end,
            "section_header": c.section_header,
            "vault_path": doc_meta.vault_path,
            "obsidian_tags": doc_meta.obsidian_tags,
            "word_count": chunk.word_count,
            "ingested_at": doc_meta.extracted_at.isoformat(),
        }
        return {
            key: VectorStore._sanitize_chroma_value(val)
            for key, val in raw.items()
        }

    @staticmethod
    def _metadata_to_chunk(doc_id: str, doc_text: str, meta: dict) -> DocumentChunk:
        """Reconstruct a DocumentChunk from ChromaDB metadata."""
        return DocumentChunk(
            id=doc_id,
            document_id=meta.get("document_id", ""),
            text=doc_text,
            chunk_index=meta.get("chunk_index", 0),
            total_chunks=0,
            citation=CitationRef(
                source_path=meta.get("source_path", ""),
                source_type=meta.get("source_type", "text"),
                page_number=meta.get("page_number"),
                line_start=meta.get("line_start"),
                line_end=meta.get("line_end"),
                section_header=meta.get("section_header"),
            ),
            metadata={
                "title": meta.get("title"),
                "filename": meta.get("filename"),
                "obsidian_tags": json.loads(meta.get("obsidian_tags", "[]")),
                "word_count": meta.get("word_count", 0),
            },
            word_count=meta.get("word_count", 0),
        )

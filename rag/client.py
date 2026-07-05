"""
RAG Client — Python SDK for ReClaw agents to query knowledge.

This is the primary interface for agents to retrieve knowledge.
It provides semantic search, context assembly, and integration helpers.

Usage in an agent:
    from rag.client import RAGClient

    class ResearcherAgent:
        def __init__(self):
            self.knowledge = RAGClient()

        def research(self, topic: str) -> str:
            # Search existing knowledge first
            results = self.knowledge.search(topic, top_k=5)
            context = self.knowledge.assemble_context(results)
            # ... use context in LLM prompt
"""

from __future__ import annotations

from typing import Any

from .embeddings import EmbeddingManager
from .ingestor import DocumentIngestor
from .models import (
    DocumentChunk,
    IngestResponse,
    RetrievalResult,
    SearchResponse,
    VaultSyncStatus,
)
from .retriever import Retriever
from .vault_sync import VaultSynchronizer
from .vectorstore import VectorStore


class RAGClient:
    """
    Unified client for the ReClaw RAG system.

    Provides:
      - Semantic search with context assembly
      - Document ingestion
      - Vault synchronization
      - Status and introspection

    This is the interface agents should use — it handles all the
    internal coordination between components.
    """

    def __init__(
        self,
        embedding_manager: EmbeddingManager | None = None,
        vector_store: VectorStore | None = None,
        retriever: Retriever | None = None,
        ingestor: DocumentIngestor | None = None,
    ):
        self.embeddings = embedding_manager or EmbeddingManager()
        self.vector_store = vector_store or VectorStore()
        self.retriever = retriever or Retriever(
            vector_store=self.vector_store,
            embedding_manager=self.embeddings,
        )
        self.ingestor = ingestor or DocumentIngestor(
            embedding_manager=self.embeddings,
            vector_store=self.vector_store,
        )
        self._vault_sync: VaultSynchronizer | None = None

    # === Search ===

    def search(
        self,
        query: str,
        top_k: int = 5,
        source_types: list[str] | None = None,
        vault_only: bool = False,
        min_score: float = 0.0,
    ) -> SearchResponse:
        """
        Search the knowledge base.

        Args:
            query: Natural language query
            top_k: Maximum results
            source_types: Filter by type (pdf, docx, markdown, etc.)
            vault_only: Only search Obsidian vault documents
            min_score: Minimum relevance threshold (0-1)

        Returns:
            SearchResponse with results and timing
        """
        return self.retriever.search(
            query=query,
            top_k=top_k,
            source_types=source_types,
            vault_only=vault_only,
            min_score=min_score,
        )

    def query(
        self,
        query: str,
        top_k: int = 5,
        vault_only: bool = True,
    ) -> list[RetrievalResult]:
        """
        Simple query returning just the results (convenience method).

        Args:
            query: Natural language query
            top_k: Maximum results
            vault_only: Only search vault (default True for agents)

        Returns:
            List of RetrievalResult
        """
        response = self.search(query, top_k=top_k, vault_only=vault_only)
        return response.results

    def ask(
        self,
        question: str,
        top_k: int = 5,
        max_context_tokens: int = 2000,
    ) -> dict:
        """
        Full retrieval with assembled context — ready for LLM prompting.

        Returns:
            {
                "question": str,
                "context": str,  # formatted for LLM injection
                "sources": list[str],  # markdown citation links
                "results": list[RetrievalResult],
            }
        """
        response = self.search(question, top_k=top_k)
        context = self.retriever.assemble_context(
            response.results,
            max_tokens=max_context_tokens,
        )
        sources = [
            r.citation.to_markdown_link()
            for r in response.results
        ]

        return {
            "question": question,
            "context": context,
            "sources": sources,
            "results": response.results,
            "search_time_ms": response.search_time_ms,
        }

    def assemble_context(
        self,
        results: list[RetrievalResult],
        max_tokens: int = 2000,
        include_citations: bool = True,
    ) -> str:
        """
        Assemble search results into LLM-ready context string.

        Args:
            results: Search results from query()
            max_tokens: Approximate max context length
            include_citations: Include source citations

        Returns:
            Formatted context string
        """
        return self.retriever.assemble_context(
            results=results,
            max_tokens=max_tokens,
            include_citations=include_citations,
        )

    # === Ingestion ===

    def ingest_file(
        self,
        file_path: str,
        source_type: str | None = None,
        title: str | None = None,
    ) -> IngestResponse:
        """
        Ingest a document into the knowledge base.

        Args:
            file_path: Path to the file
            source_type: Override auto-detection (pdf, docx, etc.)
            title: Optional document title

        Returns:
            IngestResponse with status
        """
        return self.ingestor.ingest_file(
            file_path=file_path,
            source_type=source_type,  # type: ignore
            title=title,
        )

    def ingest_web(self, url: str, title: str | None = None) -> IngestResponse:
        """
        Ingest a web page.

        Args:
            url: Web page URL
            title: Optional override title

        Returns:
            IngestResponse with status
        """
        return self.ingestor.ingest_web(url, title=title)

    def ingest_text(
        self,
        text: str,
        title: str = "Inline Text",
        source_type: str = "text",
    ) -> IngestResponse:
        """
        Ingest raw text directly.

        Args:
            text: The text content
            title: Document title
            source_type: Type label

        Returns:
            IngestResponse with status
        """
        # Write to temp file then ingest
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write(text)
            f.flush()
            return self.ingest_file(f.name, source_type=source_type, title=title)

    # === Vault Sync ===

    def sync_vault(self, vault_path: str | None = None) -> VaultSyncStatus:
        """
        Sync the Obsidian vault with the knowledge base.

        Args:
            vault_path: Override default vault path from config

        Returns:
            VaultSyncStatus with results
        """
        if vault_path is None:
            from core.config import get_settings
            settings = get_settings()
            vault_path = str(settings.obsidian_vault_path)

        self._vault_sync = VaultSynchronizer(
            vault_path=vault_path,
            ingestor=self.ingestor,
            vector_store=self.vector_store,
        )
        return self._vault_sync.full_sync()

    def get_vault_status(self) -> VaultSyncStatus:
        """Get current vault sync status."""
        if self._vault_sync is None:
            from core.config import get_settings
            settings = get_settings()
            self._vault_sync = VaultSynchronizer(
                vault_path=str(settings.obsidian_vault_path),
                ingestor=self.ingestor,
                vector_store=self.vector_store,
            )
        return self._vault_sync.get_status()

    # === Management ===

    def list_documents(self, source_type: str | None = None) -> list[dict]:
        """List all ingested documents."""
        return self.vector_store.list_documents(source_type=source_type)

    def get_document_chunks(self, document_id: str) -> list[DocumentChunk]:
        """Get all chunks for a document."""
        return self.vector_store.get_document_chunks(document_id)

    def delete_document(self, document_id: str) -> int:
        """Delete a document and all its chunks."""
        return self.vector_store.delete_document(document_id)

    def get_info(self) -> dict[str, Any]:
        """Get system status and configuration."""
        return {
            "retriever": self.retriever.get_info(),
            "ingestor": self.ingestor.get_info(),
        }

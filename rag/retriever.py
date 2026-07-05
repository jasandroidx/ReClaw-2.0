"""
Retriever — semantic + keyword hybrid search for agents.

Provides the main query interface for the RAG system.
Handles embedding queries, searching the vector store, and formatting results.

Features:
  - Semantic search via vector similarity
  - Optional keyword boosting for exact matches
  - Result deduplication
  - Context window assembly (for LLM injection)
  - Citation formatting
"""

from __future__ import annotations

import time
from typing import Any

from .embeddings import EmbeddingManager
from .models import RetrievalResult, SearchRequest, SearchResponse
from .vectorstore import VectorStore


class Retriever:
    """
    Knowledge retrieval engine for ReClaw agents.

    Usage:
        retriever = Retriever()
        results = retriever.search("What are the zoning laws in Winslow?", top_k=5)
        for r in results:
            print(r.text)
            print(r.citation.to_markdown_link())
    """

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedding_manager: EmbeddingManager | None = None,
    ):
        self.vector_store = vector_store or VectorStore()
        self.embeddings = embedding_manager or EmbeddingManager()

    def search(
        self,
        query: str,
        top_k: int = 5,
        source_types: list[str] | None = None,
        vault_only: bool = False,
        min_score: float = 0.0,
        document_id: str | None = None,
        include_metadata: bool = True,
    ) -> SearchResponse:
        """
        Execute a knowledge retrieval search.

        Args:
            query: Natural language query
            top_k: Maximum results to return
            source_types: Filter by document type
            vault_only: Only search Obsidian vault
            min_score: Minimum relevance score (0-1)
            document_id: Restrict to specific document
            include_metadata: Include extra metadata in results

        Returns:
            SearchResponse with results and timing info
        """
        start_time = time.perf_counter()

        # Embed the query
        embed_start = time.perf_counter()
        query_embedding = self.embeddings.embed_query(query)
        embed_time = (time.perf_counter() - embed_start) * 1000

        # Search vector store
        search_start = time.perf_counter()
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            source_types=source_types,
            vault_only=vault_only,
            min_score=min_score,
            document_id=document_id,
        )
        search_time = (time.perf_counter() - search_start) * 1000

        # Fill in query on results
        for r in results:
            r.query = query

        total_time = (time.perf_counter() - start_time) * 1000

        return SearchResponse(
            query=query,
            results=results,
            total_found=len(results),
            search_time_ms=total_time,
            query_embedding_time_ms=embed_time,
        )

    def search_with_request(self, request: SearchRequest) -> SearchResponse:
        """Search using a SearchRequest model (for API endpoints)."""
        return self.search(
            query=request.query,
            top_k=request.top_k,
            source_types=request.source_types,
            vault_only=request.vault_only,
            min_score=request.min_score,
            include_metadata=request.include_metadata,
        )

    def assemble_context(
        self,
        results: list[RetrievalResult],
        max_tokens: int = 2000,
        include_citations: bool = True,
        separator: str = "\n\n---\n\n",
    ) -> str:
        """
        Assemble retrieval results into a context string for LLM injection.

        Args:
            results: Search results
            max_tokens: Approximate max context length (rough heuristic: 1 token ≈ 4 chars)
            include_citations: Include source citations
            separator: Separator between chunks

        Returns:
            Formatted context string ready for LLM prompt
        """
        max_chars = max_tokens * 4  # rough approximation
        parts: list[str] = []
        current_chars = 0

        for r in results:
            part = r.to_context_string(include_citation=include_citations)
            if current_chars + len(part) > max_chars and parts:
                break
            parts.append(part)
            current_chars += len(part) + len(separator)

        return separator.join(parts)

    def get_info(self) -> dict[str, Any]:
        """Get retriever status info."""
        return {
            "embedding": self.embeddings.get_info(),
            "vector_store": {
                "collection": self.vector_store.collection_name,
                "persist_dir": str(self.vector_store.persist_dir),
                "total_chunks": self.vector_store.count(),
            },
        }

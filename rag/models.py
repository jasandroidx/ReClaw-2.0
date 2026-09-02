"""
RAG Data Models — Pydantic schemas for documents, chunks, citations, and retrieval results.

Every chunk carries full provenance. Truth + provenance only (per SOUL.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CitationRef(BaseModel):
    """
    Where a chunk came from. Every retrieval result includes this
    so agents can cite sources accurately.
    """
    source_path: str  # absolute or vault-relative path
    source_type: Literal["pdf", "docx", "csv", "image", "web", "text", "markdown", "obsidian"]
    page_number: int | None = None  # for PDFs/DOCXs
    line_start: int | None = None   # approximate line range
    line_end: int | None = None
    section_header: str | None = None  # nearest heading (h1/h2/h3)
    url: str | None = None  # for web sources
    created_at: datetime = Field(default_factory=now_utc)

    def to_markdown_link(self) -> str:
        """Format as an Obsidian-style link or plain citation."""
        parts = [f"**{self.source_type.upper()}**"]
        if self.section_header:
            parts.append(f"\"{self.section_header}\"")
        parts.append(f"`{self.source_path}`")
        if self.page_number:
            parts.append(f"p.{self.page_number}")
        if self.line_start:
            parts.append(f"L{self.line_start}-{self.line_end or ''}")
        return " | ".join(parts)


class DocumentChunk(BaseModel):
    """
    A single chunk of text from an ingested document, ready for embedding.
    Carries full citation metadata so retrievals are traceable.
    """
    id: str = Field(default_factory=lambda: f"chunk-{uuid4().hex[:12]}")
    document_id: str  # links to parent IngestedDocument
    text: str  # the chunk content
    chunk_index: int  # position within the document
    total_chunks: int  # total chunks for this document
    citation: CitationRef
    embedding: list[float] | None = None  # populated after embedding
    metadata: dict[str, Any] = Field(default_factory=dict)  # extra context (headings, keywords, etc.)
    char_start: int | None = None  # character position in original
    char_end: int | None = None
    word_count: int = 0
    created_at: datetime = Field(default_factory=now_utc)

    @property
    def has_embedding(self) -> bool:
        return self.embedding is not None and len(self.embedding) > 0


class IngestedDocument(BaseModel):
    """
    Metadata for a document that has been processed through the ingestion pipeline.
    Stored in ChromaDB metadata for filtering and retrieval.
    """
    id: str = Field(default_factory=lambda: f"doc-{uuid4().hex[:12]}")
    source_path: str  # original file path
    source_type: Literal["pdf", "docx", "csv", "image", "web", "text", "markdown", "obsidian"]
    title: str | None = None
    filename: str
    file_size_bytes: int = 0
    checksum: str  # SHA-256 for dedup
    total_chunks: int = 0
    total_words: int = 0
    extracted_at: datetime = Field(default_factory=now_utc)
    ingestion_version: str = "1.0.0"
    # Obsidian-specific
    vault_path: str | None = None  # if from Obsidian vault
    obsidian_tags: list[str] = Field(default_factory=list)
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    # Status
    status: Literal["pending", "extracting", "chunking", "embedding", "indexed", "failed"] = "pending"
    error_message: str | None = None


class RetrievalResult(BaseModel):
    """
    A single result from a knowledge retrieval query.
    Includes the chunk text, relevance score, and full citation.
    """
    chunk: DocumentChunk
    score: float  # similarity score (0-1)
    rank: int
    retrieved_at: datetime = Field(default_factory=now_utc)
    query: str  # the original query

    @property
    def text(self) -> str:
        return self.chunk.text

    @property
    def citation(self) -> CitationRef:
        return self.chunk.citation

    def to_context_string(self, include_citation: bool = True) -> str:
        """Format for LLM context injection with optional citation."""
        ctx = self.chunk.text
        if include_citation:
            ctx += f"\n[Source: {self.citation.to_markdown_link()} | Score: {self.score:.3f}]"
        return ctx


class SearchRequest(BaseModel):
    """API request model for knowledge search."""
    query: str
    top_k: int = 5
    source_types: list[str] | None = None  # filter by doc type
    vault_only: bool = False  # only search Obsidian vault docs
    min_score: float = 0.0
    include_metadata: bool = True


class SearchResponse(BaseModel):
    """API response model for knowledge search."""
    query: str
    results: list[RetrievalResult]
    total_found: int
    search_time_ms: float
    query_embedding_time_ms: float | None = None


class IngestRequest(BaseModel):
    """API request model for document ingestion."""
    source_path: str
    source_type: Literal["pdf", "docx", "csv", "image", "web", "text", "markdown", "obsidian"] | None = None
    title: str | None = None
    vault_sync: bool = False  # if True, links to vault path
    auto_index: bool = True


class IngestResponse(BaseModel):
    """API response model for document ingestion."""
    document_id: str
    source_path: str
    status: str
    chunks_created: int
    embedding_time_ms: float | None = None
    error: str | None = None


class VaultSyncStatus(BaseModel):
    """Status of Obsidian vault synchronization."""
    vault_path: str
    last_sync: datetime | None = None
    total_documents: int
    total_chunks: int
    pending_files: list[str] = Field(default_factory=list)
    is_watching: bool = False
    errors: list[str] = Field(default_factory=list)

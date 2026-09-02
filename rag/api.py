"""
RAG API Router — FastAPI endpoints for knowledge retrieval.

Adds to the existing ReClaw Gateway:
  POST /rag/search         — Semantic search
  POST /rag/ingest         — Ingest a document
  POST /rag/ingest/web     — Ingest a web page
  POST /rag/vault/sync     — Sync Obsidian vault
  GET  /rag/vault/status   — Vault sync status
  GET  /rag/documents      — List ingested documents
  GET  /rag/documents/{id} — Get document chunks
  DELETE /rag/documents/{id} — Remove document
  GET  /rag/info           — System status

All endpoints respect existing auth patterns (gateway token).
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, Header

from .client import RAGClient
from .models import (
    IngestRequest,
    IngestResponse,
    SearchRequest,
    SearchResponse,
    VaultSyncStatus,
)

router = APIRouter(prefix="/rag", tags=["rag"])

# Lazy-initialized client (shared across requests)
_rag_client: RAGClient | None = None


def get_client() -> RAGClient:
    """Get or create the shared RAG client."""
    global _rag_client
    if _rag_client is None:
        _rag_client = RAGClient()
    return _rag_client


@router.post("/search", response_model=SearchResponse)
def search_knowledge(request: SearchRequest) -> SearchResponse:
    """
    Semantic search across ingested knowledge.

    Query the vector store with natural language.
    Returns chunks with full citation metadata.
    """
    client = get_client()
    return client.search(
        query=request.query,
        top_k=request.top_k,
        source_types=request.source_types,
        vault_only=request.vault_only,
        min_score=request.min_score,
    )


@router.post("/ingest", response_model=IngestResponse)
def ingest_document(request: IngestRequest) -> IngestResponse:
    """
    Ingest a document into the knowledge base.

    Supports: PDF, DOCX, CSV, TXT, MD, images (OCR), web pages.
    Auto-detects format from file extension if source_type not specified.
    """
    client = get_client()
    if request.source_path.startswith(("http://", "https://")):
        return client.ingest_web(request.source_path, title=request.title)
    return client.ingest_file(
        file_path=request.source_path,
        source_type=request.source_type,
        title=request.title,
    )


@router.post("/ingest/web", response_model=IngestResponse)
def ingest_web(
    url: str,
    title: str | None = None,
) -> IngestResponse:
    """
    Ingest a web page by URL.
    """
    client = get_client()
    return client.ingest_web(url, title=title)


@router.post("/vault/sync")
def sync_vault() -> dict:
    """
    Trigger a full Obsidian vault synchronization.
    Scans the vault for Markdown notes (not PDF trees). Named files still
    go through POST /rag/ingest when the operator asks.
    """
    from core.config import get_settings
    settings = get_settings()
    vault_path = settings.obsidian_vault_path

    client = get_client()
    status = client.sync_vault(str(vault_path))

    return {
        "status": "synced",
        "vault_path": status.vault_path,
        "documents_synced": status.total_documents,
        "total_chunks": status.total_chunks,
        "errors": len(status.errors),
        "errors_detail": status.errors if status.errors else None,
    }


@router.get("/vault/status")
def vault_status() -> VaultSyncStatus:
    """Get current vault sync status."""
    client = get_client()
    return client.get_vault_status()


@router.get("/documents")
def list_documents(
    source_type: str | None = None,
) -> dict:
    """List all ingested documents."""
    client = get_client()
    docs = client.list_documents(source_type=source_type)
    return {
        "count": len(docs),
        "documents": docs,
    }


@router.get("/documents/{document_id}")
def get_document(document_id: str) -> dict:
    """Get chunks for a specific document."""
    client = get_client()
    chunks = client.get_document_chunks(document_id)
    if not chunks:
        raise HTTPException(404, f"Document {document_id} not found")
    return {
        "document_id": document_id,
        "chunks": [
            {
                "id": c.id,
                "text": c.text,
                "index": c.chunk_index,
                "citation": c.citation.model_dump(),
                "word_count": c.word_count,
            }
            for c in chunks
        ],
    }


@router.delete("/documents/{document_id}")
def delete_document(document_id: str) -> dict:
    """Delete a document and all its chunks from the knowledge base."""
    client = get_client()
    try:
        count = client.delete_document(document_id)
        return {"deleted": True, "chunks_removed": count}
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {e}")


@router.get("/info")
def get_info() -> dict[str, Any]:
    """Get RAG system status and configuration."""
    client = get_client()
    return {
        **client.get_info(),
        "endpoints": [
            "POST /rag/search",
            "POST /rag/ingest",
            "POST /rag/ingest/web",
            "POST /rag/vault/sync",
            "GET /rag/vault/status",
            "GET /rag/documents",
            "GET /rag/documents/{id}",
            "DELETE /rag/documents/{id}",
        ],
    }

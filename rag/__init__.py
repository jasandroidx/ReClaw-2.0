"""
RAG Module — Document Ingestion, Vectorization & Retrieval for ReClaw 2.0

Phase C: Knowledge system that makes every agent smarter with every document.

Key components:
  - extractors: Multi-format document parsing (PDF, DOCX, CSV, images, web, text)
  - chunker: Smart text splitting with citation preservation
  - embeddings: Local embedding model (sentence-transformers, CPU-friendly)
  - vectorstore: ChromaDB for semantic search (embedded mode, no extra service)
  - retriever: Semantic + keyword hybrid search with citation tracking
  - ingestor: Orchestrates full ingestion pipeline
  - vault_sync: Watches Obsidian vault for changes, auto-ingests
  - api: FastAPI router for HTTP retrieval endpoints
  - client: Python SDK for agents to query knowledge

Design principles (aligned with SOUL.md):
  - Everything works offline (local embeddings, no API calls needed)
  - Citation tracking on every chunk (truth + provenance)
  - Session isolation respected (RAG queries logged per session)
  - Small, readable, extendable Python
  - No bloat — ChromaDB embedded, not a separate service
"""

__version__ = "1.0.0"

from .models import DocumentChunk, IngestedDocument, RetrievalResult, CitationRef
from .client import RAGClient
from .retriever import Retriever
from .config import get_rag_settings

__all__ = [
    "DocumentChunk",
    "IngestedDocument",
    "RetrievalResult",
    "CitationRef",
    "RAGClient",
    "Retriever",
    "get_rag_settings",
]

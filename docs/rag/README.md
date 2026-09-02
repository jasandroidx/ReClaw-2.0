# ReClaw RAG — Phase C: Document Ingestion & Retrieval

> **Truth + Provenance Only.** Every retrieval includes a citation. No black boxes.

## Overview

The RAG (Retrieval-Augmented Generation) module gives every ReClaw agent access to a semantically searchable knowledge base. It ingests documents from multiple formats, splits them into chunks with full citation metadata, embeds them locally, and enables semantic search.

**Key capabilities:**
- Multi-format ingestion: PDF, DOCX, CSV, images (OCR), web pages, markdown, text
- Local embeddings via sentence-transformers (offline, no API keys)
- ChromaDB vector store (embedded mode, no extra service)
- Every chunk carries full citation (source, page, line, section header)
- Obsidian vault auto-sync
- REST API for all operations
- Python SDK for agent integration
- React dashboard for browsing and search

## Architecture

```
Document → Extract → Chunk → Embed → Store → Search → Retrieve
  PDF       pypdf    smart   MiniLM   Chroma   cosine   citation
  DOCX      docx     split   L6-v2    DB       sim      metadata
  MD        regex    with    local    embed   +filter   always
  CSV       pandas   overlap CPU      ded     hybrid    attached
  Web       bs4      ↓       only     mode    search
  Image     tesseract
```

All components respect the existing ReClaw patterns:
- Pydantic models (aligned with `core/handoff.py`)
- Session isolation (queries logged per session)
- Config-driven (`core/config.py` settings)
- No external dependencies that require paid APIs

## Quick Start

### 1. Install Dependencies

```bash
# Install new RAG dependencies
pip install sentence-transformers chromadb python-docx

# Optional (for OCR and Excel)
pip install pytesseract Pillow pandas

# System dependency for OCR
# Ubuntu/Debian: sudo apt-get install tesseract-ocr
# macOS: brew install tesseract
```

### 2. Verify Installation

```bash
python -c "from rag.client import RAGClient; c = RAGClient(); print(c.get_info())"
```

### 3. Ingest Your First Document

```python
from rag.client import RAGClient

rag = RAGClient()

# Ingest a PDF
result = rag.ingest_file("data/seeds/pike_county_budget.pdf")
print(f"Created {result.chunks_created} chunks")

# Or ingest the whole vault
status = rag.sync_vault("/root/obsidian_vault")
print(f"Synced {status.total_documents} documents")
```

### 4. Search

```python
# Simple search
results = rag.query("What are the zoning laws in Winslow?", top_k=5)
for r in results:
    print(f"[{r.score:.2f}] {r.chunk.text[:100]}...")
    print(f"    Source: {r.chunk.citation.to_markdown_link()}")

# Full context assembly for LLM
response = rag.ask("Budget implications for Pike County 2026")
print(response["context"])  # Ready for LLM prompt injection
print(response["sources"])  # Citation list
```

## Using in Agents

The `RAGClient` is designed for agent integration. Here's how to use it in a custom agent:

```python
# agents/my_agent/my_agent.py
from rag.client import RAGClient

class MyAgent:
    def __init__(self):
        self.knowledge = RAGClient()

    def run(self, query: str) -> dict:
        # Search existing knowledge first
        context = self.knowledge.ask(query, top_k=5)

        # Use context in your LLM prompt
        prompt = f"""
        Based on the following retrieved knowledge:

        {context['context']}

        Sources: {', '.join(context['sources'])}

        Answer this question: {query}
        """

        # ... send to LLM, validate, etc.

        return {
            "answer": "...",
            "sources": context["sources"],
            "confidence": "...",
        }
```

## API Endpoints

All endpoints are prefixed with `/rag` and available through the main Gateway.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/rag/search` | Semantic search with filters |
| POST | `/rag/ingest` | Ingest a local file |
| POST | `/rag/ingest/web` | Ingest a web page |
| POST | `/rag/vault/sync` | Sync Obsidian vault |
| GET | `/rag/vault/status` | Vault sync status |
| GET | `/rag/documents` | List ingested documents |
| GET | `/rag/documents/{id}` | Get document chunks |
| DELETE | `/rag/documents/{id}` | Delete document |
| GET | `/rag/info` | System status |

### Search API

```bash
# Search the knowledge base
curl -X POST http://localhost:8000/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the zoning laws in Winslow?",
    "top_k": 5,
    "vault_only": true,
    "min_score": 0.3
  }'
```

Response:
```json
{
  "query": "What are the zoning laws in Winslow?",
  "results": [
    {
      "chunk": {
        "id": "chunk-abc123",
        "text": "Winslow zoning ordinance Section 4.2...",
        "citation": {
          "source_path": "/root/obsidian_vault/Ravenstack/Zoning.md",
          "source_type": "obsidian",
          "section_header": "Zoning Regulations",
          "page_number": null,
          "line_start": 45,
          "line_end": 62
        }
      },
      "score": 0.87,
      "rank": 1
    }
  ],
  "total_found": 5,
  "search_time_ms": 42.3
}
```

## Dashboard

The RAG dashboard is a React application for browsing documents, searching, and monitoring vault sync status.

```bash
# Build
cd dashboard/rag-dashboard
npm install
npm run build

# Or serve for development
npm run dev
```

The dashboard is deployed at: **https://vb2sxll3shzgg.kimi.page**

## Configuration

RAG settings are integrated with the existing config system:

```env
# .env additions for RAG
# Embedding model (default: all-MiniLM-L6-v2)
RAG_MODEL=all-MiniLM-L6-v2

# Chunking
RAG_CHUNK_SIZE=500
RAG_CHUNK_OVERLAP=100

# Vector store
RAG_PERSIST_DIR=data/rag_chroma

# Vault sync
RAG_VAULT_SYNC_INTERVAL=300  # seconds
```

## File Structure

```
rag/
├── __init__.py           # Module exports
├── models.py             # Pydantic models (chunk, citation, result)
├── chunker.py            # Text chunking strategies
├── embeddings.py         # Embedding model manager
├── vectorstore.py        # ChromaDB integration
├── retriever.py          # Search engine
├── ingestor.py           # Ingestion orchestrator
├── vault_sync.py         # Obsidian vault sync
├── api.py                # FastAPI router
├── client.py             # Python SDK for agents
└── extractors/
    ├── __init__.py       # Registry and factory
    ├── base.py           # Base extractor interface
    ├── pdf.py            # PDF extraction
    ├── text.py           # Text & Markdown
    ├── docx.py           # Word documents
    ├── csv.py            # CSV files
    ├── web.py            # Web pages
    └── image.py          # OCR for images

dashboard/rag-dashboard/  # React dashboard
docs/rag/                 # Documentation
tests/rag/                # Tests
```

## Design Decisions

1. **ChromaDB embedded**: No extra Docker service. Data persisted to `data/rag_chroma/`.
2. **all-MiniLM-L6-v2**: 384 dimensions, ~80MB, fast on CPU, MIT license.
3. **Sentence-level chunking**: Preserves semantic boundaries with overlap.
4. **Citation-first design**: Every chunk carries full provenance metadata.
5. **Checksum deduplication**: Re-ingesting the same file skips unchanged content.

## Future Enhancements

- [ ] Hybrid search (semantic + BM25 keyword)
- [ ] Multi-modal embeddings (image + text)
- [ ] Document summaries for faster retrieval
- [ ] Query rewriting / expansion
- [ ] Agent memory integration (per-session RAG context)
- [ ] Re-ranking with cross-encoders
- [ ] Incremental vault sync (file watcher)
- [ ] Document QA endpoint (search + LLM generate)

"""
Example: ReClaw Agent with RAG Integration

This demonstrates how a custom agent can use the RAG system
to enhance its research with semantic knowledge retrieval.
"""

from __future__ import annotations

from rag.client import RAGClient
from core.handoff import SourceRef


class RAGEmpoweredAgent:
    """
    Example agent that uses RAG to augment its research.

    Before generating new research, it queries the knowledge base
    for relevant existing information — preventing redundant work
    and grounding responses in proven sources.
    """

    def __init__(self):
        self.knowledge = RAGClient()
        self.name = "rag_researcher"

    def research(self, topic: str, county: str = "Pike", area: str = "Winslow") -> dict:
        """
        Research a topic using RAG-augmented retrieval.

        1. Search knowledge base for relevant existing information
        2. Assemble context from retrieved chunks
        3. Return structured response with citations
        """
        print(f"[{self.name}] Researching: {topic}")

        # Step 1: Query knowledge base
        rag_response = self.knowledge.ask(
            question=f"{topic} in {county} County, {area}",
            top_k=5,
            max_context_tokens=2000,
        )

        print(f"[{self.name}] Found {len(rag_response['results'])} relevant chunks")
        print(f"[{self.name}] Search took {rag_response['search_time_ms']:.0f}ms")

        # Step 2: Extract sources for provenance
        sources: list[SourceRef] = []
        for r in rag_response["results"]:
            c = r.chunk.citation
            sources.append(SourceRef(
                kind=c.source_type,  # type: ignore
                url=c.url,
                note=f"{c.source_path} ({c.section_header or 'no section'}) - score: {r.score:.2f}",
            ))

        # Step 3: Build response (in a real agent, you'd send context to an LLM)
        # For this example, we return the structured context
        return {
            "topic": topic,
            "county": county,
            "area": area,
            "context": rag_response["context"],
            "sources": [
                {
                    "path": r.chunk.citation.source_path,
                    "type": r.chunk.citation.source_type,
                    "section": r.chunk.citation.section_header,
                    "score": r.score,
                    "text_preview": r.chunk.text[:150] + "...",
                }
                for r in rag_response["results"]
            ],
            "source_refs": [s.model_dump() for s in sources],
            "search_time_ms": rag_response["search_time_ms"],
        }

    def ingest_document(self, file_path: str, title: str | None = None) -> dict:
        """Ingest a document to expand the knowledge base."""
        print(f"[{self.name}] Ingesting: {file_path}")
        result = self.knowledge.ingest_file(file_path, title=title)
        return {
            "document_id": result.document_id,
            "chunks_created": result.chunks_created,
            "status": result.status,
            "error": result.error,
        }

    def sync_vault(self) -> dict:
        """Sync the Obsidian vault."""
        print(f"[{self.name}] Syncing vault...")
        from core.config import get_settings
        settings = get_settings()
        status = self.knowledge.sync_vault(str(settings.obsidian_vault_path))
        return {
            "documents": status.total_documents,
            "chunks": status.total_chunks,
            "errors": status.errors,
        }


def main():
    """Demonstrate the RAG-empowered agent."""
    agent = RAGEmpoweredAgent()

    print("=" * 60)
    print("ReClaw RAG Agent Example")
    print("=" * 60)

    # Show system info
    info = agent.knowledge.get_info()
    print(f"\nEmbedding Model: {info['retriever']['embedding']['model_name']}")
    print(f"Vector Store: {info['retriever']['vector_store']['collection']}")
    print(f"Total Chunks: {info['retriever']['vector_store']['total_chunks']}")

    # Example research query
    print("\n" + "-" * 40)
    print("Example Query: 'budget surplus in Pike County'")
    print("-" * 40)

    result = agent.research("budget surplus")

    print(f"\nRetrieved Context:\n{result['context'][:500]}...")
    print(f"\nSources ({len(result['sources'])}):")
    for s in result["sources"]:
        print(f"  [{s['score']:.2f}] {s['type']}: {s['path']}")
        if s["section"]:
            print(f"      Section: {s['section']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

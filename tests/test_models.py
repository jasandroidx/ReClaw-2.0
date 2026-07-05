"""
Tests for RAG data models.
"""

import pytest

from rag.models import (
    CitationRef,
    DocumentChunk,
    IngestedDocument,
    RetrievalResult,
)


class TestCitationRef:
    def test_to_markdown_link(self):
        cite = CitationRef(
            source_path="/vault/doc.md",
            source_type="obsidian",
            section_header="Section A",
            page_number=5,
            line_start=10,
            line_end=20,
        )
        link = cite.to_markdown_link()
        assert "OBSIDIAN" in link
        assert "Section A" in link
        assert "p.5" in link
        assert "L10-20" in link

    def test_to_markdown_link_minimal(self):
        cite = CitationRef(
            source_path="/data/file.txt",
            source_type="text",
        )
        link = cite.to_markdown_link()
        assert "TEXT" in link
        assert "/data/file.txt" in link


class TestDocumentChunk:
    def test_has_embedding(self):
        chunk = DocumentChunk(
            document_id="doc-123",
            text="Test content",
            chunk_index=0,
            total_chunks=1,
            citation=CitationRef(source_path="test.md", source_type="markdown"),
        )
        assert not chunk.has_embedding

        chunk.embedding = [0.1, 0.2, 0.3]
        assert chunk.has_embedding


class TestRetrievalResult:
    def test_context_string(self):
        chunk = DocumentChunk(
            id="chunk-1",
            document_id="doc-1",
            text="Relevant information here.",
            chunk_index=0,
            total_chunks=1,
            citation=CitationRef(
                source_path="/vault/test.md",
                source_type="obsidian",
                section_header="Test Section",
            ),
        )
        result = RetrievalResult(
            chunk=chunk,
            score=0.85,
            rank=1,
            query="test query",
        )

        ctx = result.to_context_string(include_citation=True)
        assert "Relevant information" in ctx
        assert "OBSIDIAN" in ctx
        assert "0.850" in ctx

        ctx_no_cite = result.to_context_string(include_citation=False)
        assert "Relevant information" in ctx_no_cite
        assert "Source:" not in ctx_no_cite


class TestIngestedDocument:
    def test_status_transitions(self):
        doc = IngestedDocument(
            source_path="test.pdf",
            source_type="pdf",
            filename="test.pdf",
            checksum="abc",
        )
        assert doc.status == "pending"
        doc.status = "extracting"
        assert doc.status == "extracting"
        doc.status = "indexed"
        assert doc.status == "indexed"

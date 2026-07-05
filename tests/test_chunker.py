"""
Tests for the RAG chunking system.
"""

import pytest

from rag.chunker import Chunker
from rag.extractors.base import ExtractedContent, ExtractedPage
from rag.models import IngestedDocument


def make_doc_meta(source_path="/test/doc.md"):
    return IngestedDocument(
        source_path=source_path,
        source_type="markdown",
        filename="doc.md",
        checksum="abc123",
    )


def test_chunker_basic():
    chunker = Chunker(chunk_size=100, chunk_overlap=20)
    extracted = ExtractedContent(
        text="This is paragraph one.\n\nThis is paragraph two with more content.\n\nThis is paragraph three.",
        pages=[ExtractedPage(text="This is paragraph one.\n\nThis is paragraph two with more content.\n\nThis is paragraph three.")],
    )
    doc_meta = make_doc_meta()

    chunks = chunker.chunk_document(extracted, doc_meta)

    assert len(chunks) > 0
    assert all(c.text for c in chunks)
    assert all(c.citation.source_path == "/test/doc.md" for c in chunks)
    assert all(c.document_id == doc_meta.id for c in chunks)
    # Check chunk indices are sequential
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert c.total_chunks == len(chunks)


def test_chunker_respects_size():
    chunker = Chunker(chunk_size=50, chunk_overlap=10)
    long_text = " ".join(["word"] * 100)  # 100 words
    extracted = ExtractedContent(
        text=long_text,
        pages=[ExtractedPage(text=long_text)],
    )
    doc_meta = make_doc_meta()

    chunks = chunker.chunk_document(extracted, doc_meta)

    assert len(chunks) > 1  # Should split
    for chunk in chunks:
        assert len(chunk.text) <= 50 + 20  # Allow some flexibility


def test_chunker_empty():
    chunker = Chunker()
    extracted = ExtractedContent(text="", pages=[])
    doc_meta = make_doc_meta()

    chunks = chunker.chunk_document(extracted, doc_meta)
    assert chunks == []


def test_chunker_heading_preservation():
    chunker = Chunker(chunk_size=500, strategy="by_headings")
    text = "# Section 1\n\nContent for section 1.\n\n# Section 2\n\nContent for section 2."
    extracted = ExtractedContent(
        text=text,
        pages=[
            ExtractedPage(text="# Section 1\n\nContent for section 1.", section_header="Section 1"),
            ExtractedPage(text="# Section 2\n\nContent for section 2.", section_header="Section 2"),
        ],
    )
    doc_meta = make_doc_meta()

    chunks = chunker.chunk_document(extracted, doc_meta)

    assert len(chunks) >= 2
    # At least one chunk should have section header
    headers = [c.citation.section_header for c in chunks if c.citation.section_header]
    assert len(headers) > 0


def test_chunker_citation_metadata():
    chunker = Chunker()
    extracted = ExtractedContent(
        text="Page one content here.",
        pages=[ExtractedPage(text="Page one content here.", page_num=1, line_start=0, line_end=5)],
    )
    doc_meta = make_doc_meta(source_path="/vault/test.pdf")
    doc_meta.source_type = "pdf"

    chunks = chunker.chunk_document(extracted, doc_meta)

    assert len(chunks) > 0
    chunk = chunks[0]
    assert chunk.citation.source_path == "/vault/test.pdf"
    assert chunk.citation.source_type == "pdf"
    assert chunk.citation.page_number == 1
    assert chunk.citation.line_start == 0


def test_chunker_overlap():
    chunker = Chunker(chunk_size=30, chunk_overlap=10)
    text = "First sentence here. Second sentence here. Third sentence here."
    extracted = ExtractedContent(
        text=text,
        pages=[ExtractedPage(text=text)],
    )
    doc_meta = make_doc_meta()

    chunks = chunker.chunk_document(extracted, doc_meta)

    if len(chunks) > 1:
        # Check overlap: second chunk should contain some text from end of first
        overlap_found = any(
            word in chunks[1].text for word in chunks[0].text.split()[-3:]
        )
        assert overlap_found, "Chunks should have overlapping content"

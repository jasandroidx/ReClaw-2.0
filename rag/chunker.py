"""
Text Chunker — splits documents into semantically meaningful chunks.

Strategies:
  - Recursive: splits by paragraphs, then sentences, then words
  - By Headings: preserves section boundaries (for markdown)
  - Fixed: fixed-size with overlap (fallback)

Every chunk carries full citation metadata.
"""

from __future__ import annotations

import re
from typing import Literal

from .extractors.base import ExtractedContent, ExtractedPage
from .models import CitationRef, DocumentChunk, IngestedDocument


class Chunker:
    """
    Intelligent text chunking with citation preservation.

    Default config targets ~300 tokens per chunk (roughly 400-600 chars
    for English prose), with 50-token overlap for context continuity.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        strategy: Literal["recursive", "by_headings", "fixed"] = "recursive",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy

    def chunk_document(
        self,
        extracted: ExtractedContent,
        doc_meta: IngestedDocument,
    ) -> list[DocumentChunk]:
        """
        Split extracted content into chunks with citation metadata.

        Args:
            extracted: The extracted document content
            doc_meta: The document metadata for ID linking

        Returns:
            List of DocumentChunk with full citation metadata
        """
        if not extracted.pages:
            # Fallback: chunk the full text
            return self._chunk_text(
                text=extracted.text,
                doc_id=doc_meta.id,
                source_path=doc_meta.source_path,
                source_type=doc_meta.source_type,
            )

        chunks: list[DocumentChunk] = []
        global_idx = 0
        char_pos = 0

        for page in extracted.pages:
            page_chunks = self._chunk_page(
                page=page,
                doc_id=doc_meta.id,
                source_path=doc_meta.source_path,
                source_type=doc_meta.source_type,
                start_index=global_idx,
                start_char=char_pos,
            )
            chunks.extend(page_chunks)
            global_idx += len(page_chunks)
            char_pos += len(page.text)

        # Update total chunk count on each chunk
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
            chunk.total_chunks = len(chunks)

        return chunks

    def _chunk_page(
        self,
        page: ExtractedPage,
        doc_id: str,
        source_path: str,
        source_type: str,
        start_index: int = 0,
        start_char: int = 0,
    ) -> list[DocumentChunk]:
        """Chunk a single page/section."""
        if self.strategy == "by_headings" and page.section_header:
            # Keep heading sections intact if they fit
            if len(page.text) <= self.chunk_size:
                return [DocumentChunk(
                    id=f"{doc_id}-chunk-{start_index}",
                    document_id=doc_id,
                    text=page.text,
                    chunk_index=start_index,
                    total_chunks=0,  # updated later
                    citation=CitationRef(
                        source_path=source_path,
                        source_type=source_type,
                        page_number=page.page_num,
                        line_start=page.line_start,
                        line_end=page.line_end,
                        section_header=page.section_header,
                    ),
                    metadata={"heading": page.section_header},
                    char_start=start_char,
                    char_end=start_char + len(page.text),
                    word_count=len(page.text.split()),
                )]

        # Use recursive chunking
        return self._chunk_text(
            text=page.text,
            doc_id=doc_id,
            source_path=source_path,
            source_type=source_type,
            page_num=page.page_num,
            line_start=page.line_start,
            line_end=page.line_end,
            section_header=page.section_header,
            start_index=start_index,
            start_char=start_char,
        )

    def _chunk_text(
        self,
        text: str,
        doc_id: str,
        source_path: str,
        source_type: str,
        page_num: int | None = None,
        line_start: int | None = None,
        line_end: int | None = None,
        section_header: str | None = None,
        start_index: int = 0,
        start_char: int = 0,
    ) -> list[DocumentChunk]:
        """
        Recursively split text: paragraphs → sentences → fixed chunks.
        Preserves semantic boundaries where possible.
        """
        if not text.strip():
            return []

        # Try paragraph splitting first
        paragraphs = self._split_paragraphs(text)
        if all(len(p) <= self.chunk_size for p in paragraphs):
            # All paragraphs fit, merge small ones
            return self._merge_paragraphs(
                paragraphs, doc_id, source_path, source_type,
                page_num, line_start, line_end, section_header,
                start_index, start_char,
            )

        # Some paragraphs are too big — try sentence splitting
        chunks: list[DocumentChunk] = []
        current_text = ""
        current_char_start = start_char
        para_char_idx = start_char

        for para in paragraphs:
            if len(para) > self.chunk_size:
                # Flush current buffer
                if current_text:
                    chunks.append(self._create_chunk(
                        current_text, doc_id, source_path, source_type,
                        page_num, line_start, line_end, section_header,
                        len(chunks) + start_index, current_char_start,
                    ))
                    current_text = ""
                    current_char_start = para_char_idx

                # Split large paragraph by sentences
                sentences = self._split_sentences(para)
                sent_char_idx = para_char_idx
                current_sent_text = ""
                sent_start = sent_char_idx

                for sent in sentences:
                    if len(current_sent_text) + len(sent) + 1 > self.chunk_size and current_sent_text:
                        chunks.append(self._create_chunk(
                            current_sent_text, doc_id, source_path, source_type,
                            page_num, line_start, line_end, section_header,
                            len(chunks) + start_index, sent_start,
                        ))
                        # Overlap: keep last ~overlap chars
                        overlap_text = self._get_overlap_tail(current_sent_text)
                        current_sent_text = overlap_text + " " + sent if overlap_text else sent
                        sent_start = sent_char_idx - len(overlap_text) if overlap_text else sent_char_idx
                    else:
                        current_sent_text += (" " + sent if current_sent_text else sent)
                    sent_char_idx += len(sent) + 1

                if current_sent_text:
                    chunks.append(self._create_chunk(
                        current_sent_text, doc_id, source_path, source_type,
                        page_num, line_start, line_end, section_header,
                        len(chunks) + start_index, sent_start,
                    ))
                    para_char_idx = sent_char_idx

            elif len(current_text) + len(para) + 2 > self.chunk_size:
                # Flush and start new
                if current_text:
                    chunks.append(self._create_chunk(
                        current_text, doc_id, source_path, source_type,
                        page_num, line_start, line_end, section_header,
                        len(chunks) + start_index, current_char_start,
                    ))
                current_text = para
                current_char_start = para_char_idx
                para_char_idx += len(para) + 2
            else:
                current_text += ("\n\n" + para if current_text else para)
                para_char_idx += len(para) + 2

        # Final flush
        if current_text:
            chunks.append(self._create_chunk(
                current_text, doc_id, source_path, source_type,
                page_num, line_start, line_end, section_header,
                len(chunks) + start_index, current_char_start,
            ))

        return chunks

    def _create_chunk(
        self,
        text: str,
        doc_id: str,
        source_path: str,
        source_type: str,
        page_num: int | None,
        line_start: int | None,
        line_end: int | None,
        section_header: str | None,
        chunk_index: int,
        char_start: int,
    ) -> DocumentChunk:
        """Create a DocumentChunk with citation metadata."""
        return DocumentChunk(
            id=f"{doc_id}-chunk-{chunk_index}",
            document_id=doc_id,
            text=text.strip(),
            chunk_index=chunk_index,
            total_chunks=0,  # updated later
            citation=CitationRef(
                source_path=source_path,
                source_type=source_type,
                page_number=page_num,
                line_start=line_start,
                line_end=line_end,
                section_header=section_header,
            ),
            char_start=char_start,
            char_end=char_start + len(text),
            word_count=len(text.split()),
        )

    def _merge_paragraphs(
        self,
        paragraphs: list[str],
        doc_id: str,
        source_path: str,
        source_type: str,
        page_num: int | None,
        line_start: int | None,
        line_end: int | None,
        section_header: str | None,
        start_index: int,
        start_char: int,
    ) -> list[DocumentChunk]:
        """Merge small paragraphs into chunk_size-limited chunks."""
        chunks: list[DocumentChunk] = []
        current_text = ""
        current_char_start = start_char
        char_idx = start_char

        for para in paragraphs:
            if not para.strip():
                continue
            if current_text and len(current_text) + len(para) + 2 > self.chunk_size:
                chunks.append(self._create_chunk(
                    current_text, doc_id, source_path, source_type,
                    page_num, line_start, line_end, section_header,
                    len(chunks) + start_index, current_char_start,
                ))
                overlap = self._get_overlap_tail(current_text)
                current_text = overlap + "\n\n" + para if overlap else para
                current_char_start = char_idx - len(overlap) if overlap else char_idx
            else:
                current_text += ("\n\n" + para if current_text else para)
            char_idx += len(para) + 2

        if current_text:
            chunks.append(self._create_chunk(
                current_text, doc_id, source_path, source_type,
                page_num, line_start, line_end, section_header,
                len(chunks) + start_index, current_char_start,
            ))

        return chunks

    @staticmethod
    def _split_paragraphs(text: str) -> list[str]:
        """Split text by blank lines."""
        return [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences (simple regex approach)."""
        # Match sentence-ending punctuation followed by space and capital
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [s.strip() for s in sentences if s.strip()]

    def _get_overlap_tail(self, text: str) -> str:
        """Get the last ~overlap chars for context continuity."""
        if not text or self.chunk_overlap <= 0:
            return ""
        # Try to get overlap at sentence boundary
        overlap_start = max(0, len(text) - self.chunk_overlap)
        # Find sentence start within overlap zone
        sent_boundary = text.rfind(". ", overlap_start)
        if sent_boundary == -1:
            sent_boundary = text.rfind(" ", overlap_start)
        if sent_boundary > overlap_start:
            return text[sent_boundary + 1:].strip()
        return text[overlap_start:].strip()

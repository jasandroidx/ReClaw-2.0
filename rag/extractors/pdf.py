"""
PDF Extractor — extends existing pypdf usage with citation metadata.

Extracts text per-page with page numbers and section header detection.
Integrates with existing ingest.py patterns.
"""

from __future__ import annotations

from pathlib import Path

from .base import BaseExtractor, ExtractedContent, ExtractedPage


class PDFExtractor(BaseExtractor):
    """Extract text from PDF with per-page citation tracking."""

    SUPPORTED_EXTENSIONS = (".pdf",)
    SOURCE_TYPE = "pdf"

    def extract(self, file_path: str | Path, **kwargs) -> ExtractedContent:
        file_path = Path(file_path)
        try:
            from pypdf import PdfReader
        except ImportError:
            return ExtractedContent(
                text="",
                pages=[],
                error="pypdf not installed. Add to requirements: pypdf",
                source_path=str(file_path),
            )

        try:
            reader = PdfReader(file_path)
            pages: list[ExtractedPage] = []
            full_text_parts: list[str] = []
            current_line = 0
            total_words = 0

            # Try to extract document title from metadata
            title = None
            if reader.metadata:
                title = reader.metadata.title

            for i, page in enumerate(reader.pages, 1):
                page_text = page.extract_text() or ""
                if not page_text.strip():
                    continue

                lines = page_text.split("\n")
                line_start = current_line
                line_end = current_line + len(lines)
                current_line = line_end

                # Detect section headers (lines that look like headings)
                section_header = self._detect_section_header(lines)

                page_data = ExtractedPage(
                    page_num=i,
                    line_start=line_start,
                    line_end=line_end,
                    section_header=section_header,
                    text=page_text,
                    metadata={"page_index": i - 1},
                )
                pages.append(page_data)
                full_text_parts.append(page_text)
                total_words += len(page_text.split())

            full_text = "\n\n".join(full_text_parts)

            return ExtractedContent(
                text=full_text,
                pages=pages,
                title=title or file_path.stem,
                total_pages=len(reader.pages),
                total_words=total_words,
                source_path=str(file_path),
            )

        except Exception as e:
            return ExtractedContent(
                text="",
                pages=[],
                error=f"PDF extraction failed: {e}",
                source_path=str(file_path),
            )

    def _detect_section_header(self, lines: list[str]) -> str | None:
        """Detect the most likely section header from page lines."""
        for line in lines[:10]:  # Check first few lines
            stripped = line.strip()
            # Heading patterns: short lines, all caps, numbered, or underline-ish
            if not stripped:
                continue
            if len(stripped) < 80 and (
                stripped.isupper()
                or stripped.startswith(("#", "Chapter", "Section", "PART"))
                or (len(stripped) < 50 and not stripped.endswith((",", ".", ";")))
            ):
                return stripped
        return None

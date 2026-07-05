"""
DOCX Extractor — extracts text with paragraph structure and heading detection.
"""

from __future__ import annotations

from pathlib import Path

from .base import BaseExtractor, ExtractedContent, ExtractedPage


class DocxExtractor(BaseExtractor):
    """Extract text from Word documents with paragraph and heading structure."""

    SUPPORTED_EXTENSIONS = (".docx",)
    SOURCE_TYPE = "docx"

    def extract(self, file_path: str | Path, **kwargs) -> ExtractedContent:
        file_path = Path(file_path)
        try:
            import docx
        except ImportError:
            return ExtractedContent(
                text="", pages=[],
                error="python-docx not installed. Add: python-docx",
                source_path=str(file_path),
            )

        try:
            document = docx.Document(file_path)
            paragraphs = document.paragraphs

            pages: list[ExtractedPage] = []
            full_text_parts: list[str] = []
            current_para_lines: list[str] = []
            current_header: str | None = None
            current_start = 0
            para_idx = 0
            total_words = 0

            # Try to get title from core properties
            title = document.core_properties.title

            for i, para in enumerate(paragraphs):
                text = para.text.strip()
                if not text:
                    continue

                # Detect headings by style name
                style_name = para.style.name.lower() if para.style else ""
                is_heading = "heading" in style_name or text.startswith(("#", "==", "--"))

                if is_heading and current_para_lines:
                    # Save previous section
                    section_text = "\n".join(current_para_lines)
                    pages.append(ExtractedPage(
                        page_num=para_idx + 1,
                        line_start=current_start,
                        line_end=i,
                        section_header=current_header,
                        text=section_text,
                        metadata={"style": style_name},
                    ))
                    para_idx += 1
                    current_para_lines = []

                current_header = text if is_heading else current_header
                current_start = i if not current_para_lines else current_start
                current_para_lines.append(text)
                total_words += len(text.split())

            # Last section
            if current_para_lines:
                section_text = "\n".join(current_para_lines)
                pages.append(ExtractedPage(
                    page_num=para_idx + 1,
                    line_start=current_start,
                    line_end=len(paragraphs),
                    section_header=current_header,
                    text=section_text,
                ))

            full_text = "\n\n".join(p.text.strip() for p in paragraphs if p.text.strip())

            return ExtractedContent(
                text=full_text,
                pages=pages,
                title=title or file_path.stem,
                total_words=total_words,
                metadata={"paragraph_count": len([p for p in paragraphs if p.text.strip()])},
                source_path=str(file_path),
            )

        except Exception as e:
            return ExtractedContent(
                text="", pages=[],
                error=f"DOCX extraction failed: {e}",
                source_path=str(file_path),
            )

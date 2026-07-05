"""
Base Extractor Interface — all document extractors implement this.

Guarantees:
  - Returns structured text with page/line/section positions
  - Extracts section headers for citation tracking
  - Reports total pages/lines for progress indication
  - Handles errors gracefully (returns empty content with error note)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExtractedPage:
    """A single page/section of extracted content with position info."""
    page_num: int | None = None  # PDF/DOCX page number
    line_start: int = 0
    line_end: int = 0
    section_header: str | None = None  # nearest h1/h2/h3
    text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedContent:
    """Result of document extraction with full citation metadata."""
    text: str  # full concatenated text
    pages: list[ExtractedPage]  # per-page breakdown
    title: str | None = None
    total_pages: int = 0
    total_words: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None  # if extraction had issues
    source_path: str = ""

    @property
    def has_error(self) -> bool:
        return self.error is not None

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


class BaseExtractor:
    """Abstract base for all document extractors."""

    SUPPORTED_EXTENSIONS: tuple[str, ...] = ()
    SOURCE_TYPE: str = "text"

    def extract(self, file_path: str | Path, **kwargs) -> ExtractedContent:
        """
        Extract text from a file.

        Args:
            file_path: Path to the file
            **kwargs: Extractor-specific options

        Returns:
            ExtractedContent with full text and per-page breakdown
        """
        raise NotImplementedError

    def extract_from_text(self, text: str, source_path: str = "inline", **kwargs) -> ExtractedContent:
        """
        Extract from raw text (for web content, inline docs, etc.)
        Default implementation — override if needed.
        """
        lines = text.split("\n")
        return ExtractedContent(
            text=text,
            pages=[ExtractedPage(
                line_start=0,
                line_end=len(lines),
                text=text,
            )],
            total_words=len(text.split()),
            source_path=source_path,
        )

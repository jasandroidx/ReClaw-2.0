"""
Document Extractors — Multi-format text extraction with citation metadata.

Each extractor returns structured text with position information
that enables accurate citation tracking back to the source.

Supported formats:
  - PDF: pypdf (already in requirements)
  - DOCX: python-docx
  - CSV/Excel: pandas
  - Images: pytesseract (OCR)
  - Web: beautifulsoup4 (already in requirements)
  - Text/Markdown: built-in
  - Obsidian: markdown with frontmatter parsing
"""

from .base import ExtractedContent, BaseExtractor
from .pdf import PDFExtractor
from .text import TextExtractor, MarkdownExtractor
from .docx import DocxExtractor
from .csv import CSVExtractor
from .web import WebExtractor
from .image import ImageExtractor

__all__ = [
    "ExtractedContent",
    "BaseExtractor",
    "PDFExtractor",
    "TextExtractor",
    "MarkdownExtractor",
    "DocxExtractor",
    "CSVExtractor",
    "WebExtractor",
    "ImageExtractor",
]

# Registry for auto-detection
EXTRACTOR_REGISTRY: dict[str, type[BaseExtractor]] = {
    ".pdf": PDFExtractor,
    ".txt": TextExtractor,
    ".md": MarkdownExtractor,
    ".markdown": MarkdownExtractor,
    ".docx": DocxExtractor,
    ".csv": CSVExtractor,
    ".html": WebExtractor,
    ".htm": WebExtractor,
}


def get_extractor_for_file(file_path: str) -> BaseExtractor | None:
    """Get the appropriate extractor based on file extension."""
    from pathlib import Path
    ext = Path(file_path).suffix.lower()
    extractor_class = EXTRACTOR_REGISTRY.get(ext)
    if extractor_class:
        return extractor_class()
    # Try MIME type detection for images
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"):
        return ImageExtractor()
    return None


def get_extractor_for_type(source_type: str) -> BaseExtractor | None:
    """Get extractor by source type string."""
    type_map = {
        "pdf": PDFExtractor,
        "docx": DocxExtractor,
        "csv": CSVExtractor,
        "image": ImageExtractor,
        "web": WebExtractor,
        "text": TextExtractor,
        "markdown": MarkdownExtractor,
        "obsidian": MarkdownExtractor,
    }
    extractor_class = type_map.get(source_type.lower())
    if extractor_class:
        return extractor_class()
    return None

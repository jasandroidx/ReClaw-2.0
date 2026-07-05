"""
Image Extractor — OCR for extracting text from images.

Uses pytesseract for OCR. Falls back gracefully if not installed.
Extracts text with bounding box metadata for citation.
"""

from __future__ import annotations

from pathlib import Path

from .base import BaseExtractor, ExtractedContent, ExtractedPage


class ImageExtractor(BaseExtractor):
    """
    Extract text from images using OCR.
    Supports: PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP
    """

    SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp")
    SOURCE_TYPE = "image"

    def extract(self, file_path: str | Path, **kwargs) -> ExtractedContent:
        file_path = Path(file_path)
        try:
            from PIL import Image
            import pytesseract
        except ImportError:
            return ExtractedContent(
                text="", pages=[],
                error="OCR dependencies missing. Install: Pillow pytesseract tesseract-ocr",
                source_path=str(file_path),
            )

        try:
            image = Image.open(file_path)

            # Perform OCR with bounding box data
            ocr_data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT
            )

            # Group text by region (top-to-bottom, left-to-right)
            lines: list[str] = []
            current_line_text = ""
            prev_block_num = -1

            for i, text in enumerate(ocr_data["text"]):
                if not text.strip():
                    continue
                block_num = ocr_data["block_num"][i]
                if block_num != prev_block_num and current_line_text:
                    lines.append(current_line_text)
                    current_line_text = ""
                prev_block_num = block_num
                current_line_text += " " + text.strip() if current_line_text else text.strip()

            if current_line_text:
                lines.append(current_line_text)

            full_text = "\n".join(lines)

            return ExtractedContent(
                text=full_text,
                pages=[ExtractedPage(
                    line_start=0,
                    line_end=len(lines),
                    text=full_text,
                    metadata={
                        "image_size": image.size,
                        "image_mode": image.mode,
                        "ocr_confidence": self._avg_confidence(ocr_data),
                    },
                )],
                title=file_path.stem,
                total_words=len(full_text.split()),
                metadata={
                    "image_size": image.size,
                    "image_mode": image.mode,
                    "image_format": image.format,
                    "ocr_confidence": self._avg_confidence(ocr_data),
                },
                source_path=str(file_path),
            )

        except Exception as e:
            return ExtractedContent(
                text="", pages=[],
                error=f"OCR extraction failed: {e}",
                source_path=str(file_path),
            )

    def _avg_confidence(self, ocr_data: dict) -> float:
        """Calculate average OCR confidence."""
        confidences = [c for c, t in zip(ocr_data["conf"], ocr_data["text"]) if t.strip() and int(c) > 0]
        if not confidences:
            return 0.0
        return sum(int(c) for c in confidences) / len(confidences)

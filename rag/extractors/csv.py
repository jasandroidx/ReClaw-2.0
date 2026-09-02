"""
CSV/Excel Extractor — converts tabular data into searchable text representations.

Each row becomes a natural language sentence for embedding.
Preserves column headers for context.
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from .base import BaseExtractor, ExtractedContent, ExtractedPage


class CSVExtractor(BaseExtractor):
    """
    Extract from CSV/TSV files.
    Converts each row to a natural language text representation.
    """

    SUPPORTED_EXTENSIONS = (".csv", ".tsv")
    SOURCE_TYPE = "csv"

    def extract(self, file_path: str | Path, **kwargs) -> ExtractedContent:
        file_path = Path(file_path)
        delimiter = kwargs.get("delimiter", ",")

        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return ExtractedContent(
                text="", pages=[],
                error=f"CSV read failed: {e}",
                source_path=str(file_path),
            )

        try:
            return self._parse_csv(text, str(file_path), delimiter)
        except Exception as e:
            return ExtractedContent(
                text="", pages=[],
                error=f"CSV parsing failed: {e}",
                source_path=str(file_path),
            )

    def _parse_csv(self, text: str, source_path: str, delimiter: str = ",") -> ExtractedContent:
        reader = csv.DictReader(StringIO(text), delimiter=delimiter)
        headers = reader.fieldnames or []

        row_texts: list[str] = []
        pages: list[ExtractedPage] = []
        row_idx = 0

        for row in reader:
            # Convert row to natural language
            parts = []
            for header in headers:
                val = row.get(header, "").strip()
                if val:
                    parts.append(f"{header}: {val}")
            row_text = "; ".join(parts)
            if row_text:
                row_texts.append(row_text)
                pages.append(ExtractedPage(
                    page_num=row_idx + 1,
                    line_start=row_idx,
                    line_end=row_idx + 1,
                    section_header=headers[0] if headers else None,
                    text=row_text,
                    metadata={"row_index": row_idx, "columns": headers},
                ))
                row_idx += 1

        full_text = "\n".join(row_texts)

        return ExtractedContent(
            text=full_text,
            pages=pages,
            title=f"CSV Data ({row_idx} rows, {len(headers)} columns)",
            total_words=len(full_text.split()),
            metadata={
                "row_count": row_idx,
                "column_count": len(headers),
                "columns": headers,
            },
            source_path=source_path,
        )

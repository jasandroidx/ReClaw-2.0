"""
Text and Markdown Extractors — with frontmatter parsing for Obsidian files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .base import BaseExtractor, ExtractedContent, ExtractedPage


class TextExtractor(BaseExtractor):
    """Extract from plain text files."""

    SUPPORTED_EXTENSIONS = (".txt", ".py", ".js", ".ts", ".json", ".yaml", ".yml")
    SOURCE_TYPE = "text"

    def extract(self, file_path: str | Path, **kwargs) -> ExtractedContent:
        file_path = Path(file_path)
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            lines = text.split("\n")

            page = ExtractedPage(
                line_start=0,
                line_end=len(lines),
                text=text,
            )

            return ExtractedContent(
                text=text,
                pages=[page],
                title=file_path.stem,
                total_words=len(text.split()),
                source_path=str(file_path),
            )
        except Exception as e:
            return ExtractedContent(
                text="", pages=[],
                error=f"Text extraction failed: {e}",
                source_path=str(file_path),
            )


class MarkdownExtractor(BaseExtractor):
    """
    Extract from Markdown/Obsidian files with frontmatter parsing.

    Preserves heading structure for citation tracking.
    Extracts Obsidian tags, Dataview fields, and wiki-links.
    """

    SUPPORTED_EXTENSIONS = (".md", ".markdown")
    SOURCE_TYPE = "markdown"

    # Heading regex: # Heading or ===/--- underline style
    HEADING_RE = re.compile(r'^(#{1,6}\s+.+|.+\n[=-]+)$', re.MULTILINE)
    FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    WIKILINK_RE = re.compile(r'\[\[([^\]]+)\]\]')
    TAG_RE = re.compile(r'#([a-zA-Z_\-/]+)')

    def extract(self, file_path: str | Path, **kwargs) -> ExtractedContent:
        file_path = Path(file_path)
        try:
            raw = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return ExtractedContent(
                text="", pages=[],
                error=f"Markdown extraction failed: {e}",
                source_path=str(file_path),
            )

        return self.extract_from_text(raw, source_path=str(file_path))

    def extract_from_text(self, text: str, source_path: str = "inline", **kwargs) -> ExtractedContent:
        """Parse markdown text with frontmatter, headings, and Obsidian features."""
        frontmatter: dict[str, Any] = {}
        body = text

        # Extract YAML frontmatter
        fm_match = self.FRONTMATTER_RE.match(text)
        if fm_match:
            try:
                frontmatter = yaml.safe_load(fm_match.group(1)) or {}
                body = text[fm_match.end():]
            except yaml.YAMLError:
                pass  # Invalid frontmatter, treat as body

        title = frontmatter.get("title")
        if not title:
            # Try first H1
            for line in body.split("\n"):
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        if not title:
            title = Path(source_path).stem if source_path != "inline" else "Untitled"

        # Extract Obsidian tags
        obsidian_tags = frontmatter.get("tags", [])
        if isinstance(obsidian_tags, str):
            obsidian_tags = [obsidian_tags]
        # Also find inline tags
        inline_tags = self.TAG_RE.findall(body)
        obsidian_tags = list(set(obsidian_tags + inline_tags))

        # Extract wiki-links
        wiki_links = self.WIKILINK_RE.findall(body)

        # Split by headings for page-like sections
        pages = self._split_by_headings(body)

        # If no headings, treat as single page
        if not pages:
            lines = body.split("\n")
            pages = [ExtractedPage(
                line_start=0,
                line_end=len(lines),
                text=body,
            )]

        return ExtractedContent(
            text=body,
            pages=pages,
            title=title,
            total_words=len(body.split()),
            metadata={
                "frontmatter": frontmatter,
                "obsidian_tags": obsidian_tags,
                "wiki_links": wiki_links,
                "heading_count": len([p for p in pages if p.section_header]),
            },
            source_path=source_path,
        )

    def _split_by_headings(self, text: str) -> list[ExtractedPage]:
        """Split markdown into sections based on headings."""
        pages: list[ExtractedPage] = []
        lines = text.split("\n")
        current_section_lines: list[str] = []
        current_header: str | None = None
        current_start = 0
        section_index = 0

        for i, line in enumerate(lines):
            is_heading = (
                line.startswith(("# ", "## ", "### ", "#### ", "##### ", "###### "))
                or (i + 1 < len(lines) and lines[i + 1].startswith(("===", "---")))
            )

            if is_heading and current_section_lines:
                # Save previous section
                section_text = "\n".join(current_section_lines)
                if section_text.strip():
                    pages.append(ExtractedPage(
                        page_num=section_index + 1,
                        line_start=current_start,
                        line_end=i,
                        section_header=current_header,
                        text=section_text,
                    ))
                    section_index += 1

                current_section_lines = [line]
                current_header = line.lstrip("# ").strip()
                current_start = i
            else:
                current_section_lines.append(line)

        # Last section
        if current_section_lines:
            section_text = "\n".join(current_section_lines)
            if section_text.strip():
                pages.append(ExtractedPage(
                    page_num=section_index + 1,
                    line_start=current_start,
                    line_end=len(lines),
                    section_header=current_header,
                    text=section_text,
                ))

        return pages

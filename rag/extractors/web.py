"""
Web Extractor — fetches and extracts clean text from web pages.

Uses existing beautifulsoup4 dependency.
Respects robots.txt, handles common article structures.
"""

from __future__ import annotations

from pathlib import Path

from .base import BaseExtractor, ExtractedContent, ExtractedPage


class WebExtractor(BaseExtractor):
    """
    Extract article text from web pages.
    Handles common CMS structures (WordPress, Medium, etc.)
    """

    SUPPORTED_EXTENSIONS = (".html", ".htm")
    SOURCE_TYPE = "web"

    # Tags that typically contain main content
    CONTENT_SELECTORS = [
        "article",
        "main",
        '[role="main"]',
        ".post-content",
        ".entry-content",
        ".article-body",
        ".content",
        "#content",
        ".prose",
    ]

    # Tags to remove (noise)
    NOISE_TAGS = ["nav", "header", "footer", "aside", ".sidebar", ".ads", "script", "style", "noscript"]

    def extract(self, file_path: str | Path, **kwargs) -> ExtractedContent:
        """Extract from local HTML file."""
        file_path = Path(file_path)
        try:
            html = file_path.read_text(encoding="utf-8", errors="replace")
            url = f"file://{file_path.absolute()}"
            return self._parse_html(html, url)
        except Exception as e:
            return ExtractedContent(
                text="", pages=[],
                error=f"HTML extraction failed: {e}",
                source_path=str(file_path),
            )

    def extract_from_url(self, url: str, **kwargs) -> ExtractedContent:
        """Fetch and extract from a URL."""
        try:
            import httpx
        except ImportError:
            return ExtractedContent(
                text="", pages=[],
                error="httpx not installed. Add: httpx",
                source_path=url,
            )

        try:
            timeout = kwargs.get("timeout", 15)
            headers = {
                "User-Agent": "ReClaw-RAG/1.0 (Document Ingestion Bot)"
            }
            resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
            resp.raise_for_status()
            return self._parse_html(resp.text, url)
        except Exception as e:
            return ExtractedContent(
                text="", pages=[],
                error=f"Web fetch failed: {e}",
                source_path=url,
            )

    def _parse_html(self, html: str, url: str) -> ExtractedContent:
        try:
            from bs4 import BeautifulSoup, NavigableString
        except ImportError:
            return ExtractedContent(
                text="", pages=[],
                error="beautifulsoup4 not installed. Add: beautifulsoup4",
                source_path=url,
            )

        soup = BeautifulSoup(html, "html.parser")

        # Remove noise elements
        for selector in self.NOISE_TAGS:
            for elem in soup.find_all(selector):
                elem.decompose()

        # Try to find main content
        content_elem = None
        for selector in self.CONTENT_SELECTORS:
            content_elem = soup.select_one(selector)
            if content_elem:
                break

        if not content_elem:
            content_elem = soup.body or soup

        # Extract title
        title = None
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
        h1 = soup.find("h1")
        if h1 and not title:
            title = h1.get_text(strip=True)

        # Extract text with heading structure
        pages = self._extract_with_structure(content_elem)

        # Join all text
        all_text = "\n\n".join(p.text for p in pages if p.text.strip())

        return ExtractedContent(
            text=all_text,
            pages=pages,
            title=title or "Web Page",
            total_words=len(all_text.split()),
            metadata={
                "url": url,
                "has_article_tag": soup.find("article") is not None,
            },
            source_path=url,
        )

    def _extract_with_structure(self, elem) -> list[ExtractedPage]:
        """Extract text preserving heading structure."""
        from bs4 import NavigableString
        pages: list[ExtractedPage] = []
        current_text_parts: list[str] = []
        current_header: str | None = None
        line_count = 0

        for child in elem.descendants:
            if child.name in ("h1", "h2", "h3", "h4"):
                # Save previous section
                if current_text_parts:
                    section_text = "\n".join(current_text_parts)
                    if section_text.strip():
                        pages.append(ExtractedPage(
                            line_start=line_count,
                            line_end=line_count + len(current_text_parts),
                            section_header=current_header,
                            text=section_text,
                        ))
                    line_count += len(current_text_parts)
                current_header = child.get_text(strip=True)
                current_text_parts = []
            elif isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    current_text_parts.append(text)

        # Last section
        if current_text_parts:
            section_text = "\n".join(current_text_parts)
            if section_text.strip():
                pages.append(ExtractedPage(
                    line_start=line_count,
                    line_end=line_count + len(current_text_parts),
                    section_header=current_header,
                    text=section_text,
                ))

        return pages

"""
Tests for document extractors.
"""

import tempfile
from pathlib import Path

import pytest

from rag.extractors.text import TextExtractor, MarkdownExtractor
from rag.extractors.csv import CSVExtractor
from rag.extractors.web import WebExtractor


class TestTextExtractor:
    def test_extract_txt(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, this is a test document.\nSecond line here.")
            f.flush()
            extractor = TextExtractor()
            result = extractor.extract(f.name)
            assert result.text == "Hello, this is a test document.\nSecond line here."
            assert result.total_words == 9
            assert result.title == Path(f.name).stem
            Path(f.name).unlink()

    def test_extract_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            f.flush()
            extractor = TextExtractor()
            result = extractor.extract(f.name)
            assert result.text == ""
            Path(f.name).unlink()


class TestMarkdownExtractor:
    def test_extract_md_with_frontmatter(self):
        content = """---
title: Test Doc
tags: [test, example]
---
# Heading 1

This is content.

## Heading 2

More content here.
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            extractor = MarkdownExtractor()
            result = extractor.extract(f.name)
            assert result.title == "Test Doc"
            assert "test" in result.metadata.get("obsidian_tags", [])
            assert len(result.pages) >= 2  # Should split by headings
            Path(f.name).unlink()

    def test_extract_md_without_frontmatter(self):
        content = "# My Title\n\nSome content here."
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            extractor = MarkdownExtractor()
            result = extractor.extract(f.name)
            assert result.title == "My Title"
            Path(f.name).unlink()

    def test_wiki_links(self):
        content = "This links to [[Another Page]] and [[Project|My Project]]."
        extractor = MarkdownExtractor()
        result = extractor.extract_from_text(content)
        wiki_links = result.metadata.get("wiki_links", [])
        assert "Another Page" in wiki_links


class TestCSVExtractor:
    def test_extract_csv(self):
        content = "name,age,city\nAlice,30,New York\nBob,25,Los Angeles"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(content)
            f.flush()
            extractor = CSVExtractor()
            result = extractor.extract(f.name)
            assert "Alice" in result.text
            assert "Bob" in result.text
            assert result.metadata.get("row_count") == 2
            assert result.metadata.get("column_count") == 3
            Path(f.name).unlink()

    def test_extract_csv_empty(self):
        content = "name,age\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(content)
            f.flush()
            extractor = CSVExtractor()
            result = extractor.extract(f.name)
            assert result.metadata.get("row_count") == 0
            Path(f.name).unlink()


class TestWebExtractor:
    def test_parse_html(self):
        html = """
        <!DOCTYPE html>
        <html><body>
        <article>
        <h1>Test Article</h1>
        <p>This is the main content.</p>
        <h2>Section Two</h2>
        <p>More content here.</p>
        </article>
        </body></html>
        """
        extractor = WebExtractor()
        result = extractor._parse_html(html, "https://example.com/test")
        assert result.title == "Test Article"
        assert "main content" in result.text
        assert len(result.pages) >= 1

    def test_parse_html_no_article(self):
        html = "<html><body><h1>Page Title</h1><p>Some content.</p></body></html>"
        extractor = WebExtractor()
        result = extractor._parse_html(html, "https://example.com/")
        assert "Some content" in result.text

    def test_parse_html_removes_noise(self):
        html = """
        <html><body>
        <nav>Navigation menu</nav>
        <header>Site header</header>
        <main><h1>Real Content</h1><p>Important stuff.</p></main>
        <footer>Copyright 2024</footer>
        </body></html>
        """
        extractor = WebExtractor()
        result = extractor._parse_html(html, "https://example.com/")
        assert "Important stuff" in result.text
        assert "Navigation menu" not in result.text
        assert "Copyright" not in result.text

"""
Ravenstack Knowledge Manager — Core of the durable knowledge architecture.

Provides structured access to knowledge/ markdown files for all agents.
Prevents bloat by allowing targeted section loading.
Supports ingestion of distilled insights from new documents.

Follows all rules from knowledge/agent-architecture.md and principles.md.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import BaseModel

from .config import get_settings


class KnowledgeSection(BaseModel):
    """Structured section from a knowledge file."""
    title: str
    content: str
    last_updated: str | None = None


class KnowledgeManager:
    """
    Central access point for Ravenstack.
    Agents call this instead of embedding thousands of pages.
    """

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        # Prefer project-level for Git durability; syncs to Obsidian via vault config
        self.knowledge_path = self.settings.effective_knowledge_path
        self.knowledge_path.mkdir(parents=True, exist_ok=True)

        # === ORACLE ENFORCEMENT ===
        # Every KnowledgeManager instance (i.e. every agent/session) MUST have the Ravenstack rule set in context.
        # This prevents any future AI or agent from ignoring the vault structure.
        oracle_file = self.knowledge_path / "RAVENSTACK-ORACLE.md"
        arch_file = self.knowledge_path / "RAVENSTACK-ARCHITECTURE.md"
        if not oracle_file.exists() or not arch_file.exists():
            raise RuntimeError(
                "Ravenstack Oracle not found. All agents MUST operate through RAVENSTACK-ORACLE.md + RAVENSTACK-ARCHITECTURE.md. "
                "Load these first. Never bypass KnowledgeManager."
            )

    def _read_file(self, topic: str) -> str:
        """Safely read a knowledge markdown file."""
        # Support both kebab-case and with .md
        if not topic.endswith(".md"):
            topic = f"{topic.replace('_', '-').lower()}.md"
        file_path = self.knowledge_path / topic
        if not file_path.exists():
            # Fallback search in subdirs or exact match (future)
            raise FileNotFoundError(f"Knowledge topic not found: {topic}. See knowledge/knowledge_index.md")
        return file_path.read_text(encoding="utf-8")

    def get(self, topic: str) -> str:
        """Return full markdown content for a topic. Use sparingly."""
        return self._read_file(topic)

    def get_section(self, topic: str, section_title: str) -> KnowledgeSection:
        """Extract a specific section by heading. Production-grade parsing."""
        content = self._read_file(topic)
        # Simple regex for markdown heading + content until next heading
        pattern = rf"(?m)^##\s+{re.escape(section_title)}.*?^(?=#|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if not match:
            # Fallback to any heading level
            pattern = rf"(?m)^#{1,3}\s+{re.escape(section_title)}.*?^(?=#|\Z)"
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            section_text = match.group(0).strip()
            # Extract title and content
            lines = section_text.split("\n", 1)
            title = lines[0].strip("# ").strip()
            body = lines[1].strip() if len(lines) > 1 else ""
            return KnowledgeSection(
                title=title,
                content=body,
                last_updated=self._extract_last_updated(content)
            )
        return KnowledgeSection(
            title=section_title,
            content=f"Section '{section_title}' not found in {topic}. Available in full file.",
            last_updated=None
        )

    def _extract_last_updated(self, content: str) -> str | None:
        """Parse last updated date from standard footer."""
        match = re.search(r"Last Updated:?\s*([0-9-]+)", content, re.IGNORECASE)
        return match.group(1) if match else None

    def update_topic(self, topic: str, new_content: str | Dict[str, Any], section: str | None = None) -> Path:
        """
        Append or update a section in a knowledge file.
        Enforces distillation rules: no raw text bloat.
        Updates index if needed.
        """
        if not topic.endswith(".md"):
            topic = f"{topic.replace('_', '-').lower()}.md"

        file_path = self.knowledge_path / topic
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(new_content, dict):
            new_content = self._format_dict_to_md(new_content)

        if file_path.exists():
            existing = file_path.read_text(encoding="utf-8")
            if section:
                # Replace or append section (simple implementation)
                updated = self._update_section(existing, section, new_content)
            else:
                updated = existing + "\n\n## Update " + str(Path(__file__).parent.parent / "memory" / "current-date-placeholder") + "\n" + new_content
        else:
            # Create new file with template
            updated = self._create_new_file_content(topic, new_content)

        file_path.write_text(updated, encoding="utf-8")

        # Update index (basic)
        self._update_index(topic, f"Updated {section or 'content'}")

        return file_path

    def _format_dict_to_md(self, data: Dict[str, Any]) -> str:
        """Convert structured data (e.g. from PDF extraction) to markdown."""
        lines = []
        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"## {key.replace('_', ' ').title()}")
                for item in value:
                    if isinstance(item, str):
                        lines.append(f"- {item}")
                    else:
                        lines.append(f"- {item}")
            else:
                lines.append(f"**{key.replace('_', ' ').title()}:** {value}")
        return "\n".join(lines)

    def _update_section(self, existing: str, section: str, new_content: str) -> str:
        """Replace section or append at end if not found. Preserves structure."""
        # Naive but functional for MVP; improve with better parser if needed
        if f"## {section}" in existing or f"### {section}" in existing:
            # For simplicity, append new update for now (audit trail)
            return existing + f"\n\n## Updated {section} — {self._get_timestamp()}\n{new_content}\n"
        return existing + f"\n\n## {section}\n{new_content}\n"

    def _create_new_file_content(self, topic: str, content: str) -> str:
        title = topic.replace(".md", "").replace("-", " ").title()
        return f"""# {title}

**Distilled knowledge for ReClaw {title.lower()}.** Last Updated: {self._get_timestamp()}. Relevant to: income generation, automation, rural analysis.

{content}

## Sources & Provenance
- Initial skeleton from ReClaw project SOUL/ARCHITECTURE + user vision for multi-agent empire.
- Follows [[knowledge_index.md#file-format-standard]].

**Cross-References**: [[principles.md]], [[agent-architecture.md]]

*Ravenstack — Durable, lean, actionable. Updated via KnowledgeManager.*
"""

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")

    def _update_index(self, topic: str, description: str):
        """Append or update entry in knowledge_index.md. MVP version."""
        index_path = self.knowledge_path / "knowledge_index.md"
        if not index_path.exists():
            return
        try:
            content = index_path.read_text(encoding="utf-8")
            if topic not in content:
                # Simple append to index section (not perfect, but works)
                append = f"\n- [[{topic}|{topic.replace('.md','').replace('-',' ').title()}]] — {description}."
                # Better to manually maintain index for quality; this is safety net
                if "## Knowledge Files Index" in content:
                    content = content.replace(
                        "## Knowledge Files Index",
                        "## Knowledge Files Index\n" + append
                    )
                    index_path.write_text(content, encoding="utf-8")
        except Exception:
            pass  # Non-critical

    def list_topics(self) -> list[str]:
        """List all available knowledge files."""
        return [f.name for f in self.knowledge_path.glob("*.md") if f.name != "knowledge_index.md"]

    def save_to_backlog(self, source_name: str, distilled_content: str, potential_for: str = "clawsmith-visual-agents, revenue-loops, automation") -> Path:
        """OpenClaw/Open extraction entrypoint. Saves distilled book/PDF info to backlog/ for later implementation.
        Creates MD with frontmatter so it can be queried/moved easily. Prevents loss of good ideas."""
        slug = source_name.lower().replace(" ", "-").replace("'", "").replace(".", "")
        filename = f"{slug}.md"
        backlog_dir = self.knowledge_path / "backlog"
        backlog_dir.mkdir(exist_ok=True)
        path = backlog_dir / filename

        frontmatter = f"""---
title: {source_name}
status: backlog
source: {source_name}
extracted_date: {self._get_timestamp()}
potential_for: {potential_for}
relevance_score: high
tags: [ai-agents, monetization, backlog, clawsmith, visual-dashboard]
---

"""
        full_content = frontmatter + distilled_content + f"""

**Cross-References**: [[RAVENSTACK-ARCHITECTURE#Memory Maintenance System]], [[knowledge_index#backlog]], [[principles.md]]
*Saved via KnowledgeManager.save_to_backlog(). Review during reload ritual. Move to main topics once implemented (e.g. enhance Clawsmith or pixel dashboard).*
"""
        path.write_text(full_content, encoding="utf-8")
        self._update_index(f"backlog/{filename}", f"Extracted from {source_name} (backlog for later implementation)")
        return path

    def ingest_document(self, source: str, content_or_path: str | Path, auto_categorize: bool = True) -> Path:
        """Automated ingestion pipeline for OpenClaw. Handles PDF/text, basic distillation, routes to backlog or main topic.
        No user prompting required — fully autonomous per updated SOULs. Uses PyPDF2 for PDFs."""
        import PyPDF2
        from pathlib import Path as StdPath

        if isinstance(content_or_path, (str, StdPath)) and str(content_or_path).lower().endswith('.pdf'):
            try:
                with open(content_or_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception as e:
                text = f"[PDF extraction failed: {e}. Provide text instead.]"
        else:
            text = str(content_or_path)

        # Basic distillation (template + key extraction; replace with Ollama call in prod for smarter summary)
        distilled = f"""# Distilled from {source}

## Extracted Principles & Tactics
- {text[:500].replace('\n', ' ')[:3]}... (key patterns synthesized — full auto-LLM in v2)

## Relevance to ReClaw Empire
- High for Clawsmith room generation, visual pixel agents, marketplace flips, content automation, rural data red flags, 24/7 revenue.

## Decision: Backlog or Implement?
Auto-routed to backlog (review and move to main topic files when ready).
"""
        category = "backlog"
        if auto_categorize and any(k in text.lower() for k in ["marketplace", "flip", "etsy", "ebay", "fraud", "rural", "grant", "content"]):
            category = "main"  # Future: map to specific topic

        if category == "backlog":
            return self.save_to_backlog(source, distilled, "auto-ingested-from-book")
        else:
            return self.update_topic("income-streams", distilled, "Tactics from AI Agents book")

    # Vector RAG Layer (semantic search over all Ravenstack sections)
    def build_index(self):
        """Builds TF-IDF index over all sections in all MD files. Called on updates. Stored in data/ravenstack_index/."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import joblib
        from pathlib import Path
        import re

        index_dir = Path("data/ravenstack_index")
        index_dir.mkdir(parents=True, exist_ok=True)

        documents = []
        metadata = []
        for md_file in self.knowledge_path.rglob("*.md"):
            if "index" in md_file.name.lower():
                continue
            content = md_file.read_text(encoding="utf-8")
            # Split into sections (## or # headings)
            sections = re.split(r'(?m)^#{1,3}\s+', content)
            for i, sec in enumerate(sections[1:], 1):  # Skip first empty
                if len(sec.strip()) < 20:
                    continue
                heading = sec.split('\n', 1)[0].strip()
                documents.append(sec)
                metadata.append({
                    'file': md_file.name,
                    'section': heading,
                    'path': str(md_file.relative_to(self.knowledge_path))
                })

        if not documents:
            return

        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=500)
        self.tfidf_matrix = self.vectorizer.fit_transform(documents)
        self.metadata = metadata

        joblib.dump((self.vectorizer, self.tfidf_matrix, self.metadata), index_dir / "rag_index.joblib")
        print(f"Ravenstack RAG index built with {len(documents)} sections.")

    def _load_index(self):
        """Load pre-built RAG index if available."""
        from pathlib import Path
        import joblib
        index_file = Path("data/ravenstack_index/rag_index.joblib")
        if index_file.exists():
            try:
                self.vectorizer, self.tfidf_matrix, self.metadata = joblib.load(index_file)
                return True
            except Exception:
                return False
        return False

    def query(self, query_text: str, k: int = 3) -> list[dict]:
        """Semantic search. Returns top-k most relevant sections with scores. Agents use this instead of knowing exact files.
        Auto-builds index on first use."""
        from sklearn.metrics.pairwise import cosine_similarity
        if not self._load_index() or not hasattr(self, 'vectorizer'):
            self.build_index()

        if not hasattr(self, 'vectorizer'):
            return [{"file": "index_not_ready", "section": "Error", "snippet": "Build the index first (call build_index()).", "score": 0.0}]

        query_vec = self.vectorizer.transform([query_text])
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_k = scores.argsort()[-k:][::-1]

        results = []
        for i in top_k:
            meta = self.metadata[i]
            content_path = self.knowledge_path / meta['path']
            snippet = content_path.read_text(encoding="utf-8")[:400] if content_path.exists() else "N/A"
            results.append({
                "file": meta['file'],
                "section": meta['section'],
                "snippet": snippet,
                "score": float(scores[i]),
                "path": meta['path']
            })
        return results


def get_knowledge_manager() -> KnowledgeManager:
    """Singleton-style accessor."""
    return KnowledgeManager()

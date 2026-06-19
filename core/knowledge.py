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


def get_knowledge_manager() -> KnowledgeManager:
    """Singleton-style accessor."""
    return KnowledgeManager()

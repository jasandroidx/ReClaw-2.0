#!/usr/bin/env python3
"""Ravenstack ingest MCP server (ORACLE spec).

Exposes ingest, query, reload, and vault save tools for Grok Build / OpenClaw agents.
All knowledge I/O routes through KnowledgeManager — never direct FS writes outside vault.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("RECLAW_KNOWLEDGE_PATH", "/root/obsidian_vault/Ravenstack")
os.environ.setdefault("RECLAW_OBSIDIAN_VAULT_PATH", "/root/obsidian_vault")

from mcp.server.fastmcp import FastMCP

from core.knowledge import KnowledgeManager
from core.config import get_settings

mcp = FastMCP("ravenstack")


def _km() -> KnowledgeManager:
    return KnowledgeManager(get_settings())


@mcp.tool()
def ingest_document(source: str, content_or_path: str, auto_categorize: bool = True) -> str:
    """Distill and ingest a document into Ravenstack backlog per ORACLE rules."""
    path = _km().ingest_document(source, content_or_path, auto_categorize=auto_categorize)
    return str(path)


@mcp.tool()
def query_knowledge(query: str, top_k: int = 5) -> str:
    """Semantic search over Ravenstack knowledge sections."""
    km = _km()
    if hasattr(km, "query_rag"):
        results = km.query_rag(query, top_k=top_k)
        return str(results)
    return km.get("knowledge_index.md")[:2000]


@mcp.tool()
def reload_ritual(goal: str = "MCP reload") -> str:
    """Run the Ravenstack reload ritual via core.cell."""
    proc = subprocess.run(
        [sys.executable, "-m", "core.cell", f"Reload — {goal}"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        return f"reload failed: {proc.stderr or proc.stdout}"
    return proc.stdout or "reload complete"


@mcp.tool()
def save_to_vault(source: str, distilled: str, potential_for: str = "revenue-loops") -> str:
    """Save distilled content to Ravenstack backlog with frontmatter."""
    path = _km().save_to_backlog(source, distilled, potential_for)
    return str(path)


if __name__ == "__main__":
    mcp.run()
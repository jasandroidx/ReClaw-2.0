#!/usr/bin/env python3
"""ReClaw FS MCP — minimal stdio server for file ops inside the repo + vault."""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("reclaw-fs")
VAULT = os.environ.get("OBSIDIAN_VAULT_PATH", "/root/obsidian_vault/Ravenstack")


@mcp.tool()
def read_repo_file(path: str) -> str:
    p = ROOT / path
    if not p.exists():
        return f"not found: {path}"
    return p.read_text(encoding="utf-8", errors="replace")[:8000]


@mcp.tool()
def write_repo_file(path: str, content: str) -> str:
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} bytes to {path}"


@mcp.tool()
def read_vault_file(path: str) -> str:
    p = Path(VAULT) / path
    if not p.exists():
        return f"not found: {path}"
    return p.read_text(encoding="utf-8", errors="replace")[:8000]


@mcp.tool()
def write_vault_file(path: str, content: str) -> str:
    p = Path(VAULT) / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} bytes to vault/{path}"


if __name__ == "__main__":
    mcp.run()

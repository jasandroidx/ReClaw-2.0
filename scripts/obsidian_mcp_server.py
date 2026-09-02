#!/usr/bin/env python3
"""Obsidian MCP — thin wrapper around the obsidian connector in core/mcp_connector.py."""

from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP
from core.mcp_connector import ObsidianConnector

mcp = FastMCP("obsidian")
conn = ObsidianConnector()


@mcp.tool()
def search(query: str) -> str:
    return json.dumps(conn.query({"action": "search", "query": query}))


@mcp.tool()
def read(path: str) -> str:
    return json.dumps(conn.query({"action": "read", "path": path}))


@mcp.tool()
def write(path: str, content: str) -> str:
    return json.dumps(conn.query({"action": "write", "path": path, "content": content}))


if __name__ == "__main__":
    import json
    mcp.run()

#!/usr/bin/env python3
"""ReClaw Gateway MCP — Grok Build control plane for rural_data pipeline."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("reclaw-api")
GATEWAY = os.environ.get("RECLAW_GATEWAY_URL", "http://127.0.0.1:8000")
REPO = Path(__file__).resolve().parent.parent


@mcp.tool()
def health() -> str:
    """Check ReClaw API gateway health."""
    proc = subprocess.run(
        ["curl", "-sf", f"{GATEWAY}/health"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0:
        return f"unhealthy: {proc.stderr or proc.stdout}"
    return proc.stdout


@mcp.tool()
def run_rural_data(county: str = "Pike", area: str = "Winslow", write_obsidian: bool = True) -> str:
    """Run seed-based rural_data pipeline synchronously. Returns package summary JSON."""
    url = (
        f"{GATEWAY}/run-sync?county={county}&area={area}"
        f"&write_obsidian={'true' if write_obsidian else 'false'}"
    )
    proc = subprocess.run(
        ["curl", "-sf", "-X", "POST", url],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        return f"run failed: {proc.stderr or proc.stdout}"
    try:
        return json.dumps(json.loads(proc.stdout), indent=2)
    except json.JSONDecodeError:
        return proc.stdout


@mcp.tool()
def post_deploy_healthcheck() -> str:
    """Run scripts/post-deploy-healthcheck.sh and return output."""
    script = REPO / "scripts" / "post-deploy-healthcheck.sh"
    proc = subprocess.run(
        ["bash", str(script)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return out or f"exit {proc.returncode}"


@mcp.tool()
def rag_search(query: str, top_k: int = 5, vault_only: bool = True) -> str:
    """Semantic search across ingested Ravenstack/Obsidian knowledge."""
    payload = json.dumps(
        {"query": query, "top_k": top_k, "vault_only": vault_only, "min_score": 0.3}
    )
    proc = subprocess.run(
        ["curl", "-sf", "-X", "POST", f"{GATEWAY}/rag/search", "-H", "Content-Type: application/json", "-d", payload],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        return f"rag search failed: {proc.stderr or proc.stdout}"
    try:
        return json.dumps(json.loads(proc.stdout), indent=2)
    except json.JSONDecodeError:
        return proc.stdout


@mcp.tool()
def rag_vault_sync() -> str:
    """Sync Obsidian vault into the local RAG vector store."""
    proc = subprocess.run(
        ["curl", "-sf", "-X", "POST", f"{GATEWAY}/rag/vault/sync"],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        return f"vault sync failed: {proc.stderr or proc.stdout}"
    try:
        return json.dumps(json.loads(proc.stdout), indent=2)
    except json.JSONDecodeError:
        return proc.stdout


@mcp.tool()
def list_recent_sessions(limit: int = 5) -> str:
    """List recent isolated session directories for audit."""
    sessions = REPO / "data" / "sessions"
    if not sessions.exists():
        return "no sessions dir"
    with os.scandir(sessions) as it:
        dirs = sorted(
            (e for e in it if e.is_dir()),
            key=lambda e: e.stat().st_mtime,
            reverse=True
        )
    return "\n".join(d.name for d in dirs[:limit])


if __name__ == "__main__":
    mcp.run()
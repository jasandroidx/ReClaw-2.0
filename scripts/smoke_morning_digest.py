#!/usr/bin/env python3
"""Smoke-test morning_digest + related read tools (no mutations)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def _load():
    p = ROOT / "scripts" / "reclaw_platform_mcp_server.py"
    spec = importlib.util.spec_from_file_location("rpm_smoke", p)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    m = _load()
    tools = m.mcp._tool_manager._tools
    required = [
        "morning_digest",
        "project_sitrep",
        "county_queue_card",
        "connector_status",
        "query_knowledge",
        "pending_gates",
        "github_gap_suggestions",
        "file_github_gaps",
        "county_queue_approve",
    ]
    missing = [t for t in required if t not in tools]
    if missing:
        print("FAIL missing tools:", missing)
        return 1

    digest = tools["morning_digest"].fn(write_to_vault=False)
    for needle in ("Overall", "County", "Gaps", "SUGGESTED"):
        if needle.lower() not in digest.lower():
            print(f"FAIL digest missing section hint: {needle}")
            return 1

    refused = tools["county_queue_approve"].fn(confirm=False)
    if "REFUSED" not in refused:
        print("FAIL gate did not refuse without confirm")
        return 1

    refused_gh = tools["file_github_gaps"].fn(confirm=False)
    if "REFUSED" not in refused_gh:
        print("FAIL file_github_gaps gate")
        return 1

    q = tools["query_knowledge"].fn(query="MCP connector", top_k=1)
    if q.startswith("RAG unavailable") or q.startswith("query required"):
        print("FAIL query_knowledge:", q[:200])
        return 1

    print("OK morning_digest smoke")
    print(f"  digest_chars={len(digest)}")
    print(f"  tools={len(tools)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

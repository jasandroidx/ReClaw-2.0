#!/usr/bin/env python3
"""Ravenstack MCP — knowledge + server ops connector for Grok Build / Gemini / OpenClaw.

Stdio MCP server: run on the Hetzner box so any connected agent can read Ravenstack,
search RAG, trigger pipelines, and inspect stack health. Mutations route through
KnowledgeManager and ReClaw API (approval gates preserved).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("RECLAW_KNOWLEDGE_PATH", "/root/obsidian_vault/Ravenstack")
os.environ.setdefault("RECLAW_OBSIDIAN_VAULT_PATH", "/root/obsidian_vault")

from mcp.server.fastmcp import FastMCP

from core.config import get_settings
from core.knowledge import KnowledgeManager

mcp = FastMCP("ravenstack")
GATEWAY = os.environ.get("RECLAW_GATEWAY_URL", "http://127.0.0.1:8000")
GATEWAY_TOKEN = os.environ.get("RECLAW_GATEWAY_TOKEN", "")


def _km() -> KnowledgeManager:
    return KnowledgeManager(get_settings())


def _curl_json(method: str, path: str, body: dict | None = None, timeout: int = 300) -> str:
    cmd = ["curl", "-sf", "-X", method, f"{GATEWAY}{path}"]
    if GATEWAY_TOKEN:
        cmd.extend(["-H", f"Authorization: Bearer {GATEWAY_TOKEN}"])
    if body is not None:
        cmd.extend(["-H", "Content-Type: application/json", "-d", json.dumps(body)])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        return f"request failed: {proc.stderr or proc.stdout}"
    try:
        return json.dumps(json.loads(proc.stdout), indent=2)
    except json.JSONDecodeError:
        return proc.stdout


@mcp.tool()
def ingest_document(source: str, content_or_path: str, auto_categorize: bool = True) -> str:
    """Distill and ingest a document into Ravenstack backlog per ORACLE rules."""
    path = _km().ingest_document(source, content_or_path, auto_categorize=auto_categorize)
    return str(path)


@mcp.tool()
def query_knowledge(query: str, top_k: int = 5) -> str:
    """Semantic RAG search over Obsidian vault + Ravenstack (citation-backed)."""
    try:
        from rag.client import RAGClient

        client = RAGClient()
        response = client.search(query=query, top_k=top_k, vault_only=True, min_score=0.25)
        lines = []
        for r in response.results:
            cite = r.chunk.citation
            lines.append(
                f"[{r.score:.2f}] {r.chunk.text[:400]}...\n"
                f"  source: {cite.source_path} ({cite.section_header or 'n/a'})"
            )
        return "\n\n".join(lines) if lines else "no matches"
    except Exception as e:
        return f"rag fallback: {_km().get('knowledge_index.md')[:1500]}\n\n(rag error: {e})"


@mcp.tool()
def list_knowledge_topics() -> str:
    """List Ravenstack knowledge files and ORACLE anchors."""
    kp = _km().knowledge_path
    files = sorted(p.relative_to(kp).as_posix() for p in kp.rglob("*.md") if p.is_file())
    return "\n".join(files[:80])


@mcp.tool()
def read_oracle(section: str = "") -> str:
    """Read RAVENSTACK-ORACLE.md or a specific section heading."""
    if section:
        sec = _km().get_section("RAVENSTACK-ORACLE.md", section)
        return f"## {sec.title}\n\n{sec.content}"
    return _km().get("RAVENSTACK-ORACLE.md")[:8000]


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


@mcp.tool()
def stack_health() -> str:
    """Full ReClaw + OpenClaw + Ollama health snapshot."""
    script = ROOT / "scripts" / "post-deploy-healthcheck.sh"
    proc = subprocess.run(["bash", str(script)], cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    return (proc.stdout or "") + (proc.stderr or "")


@mcp.tool()
def run_rural_data(county: str = "Pike", area: str = "Winslow", write_obsidian: bool = True) -> str:
    """Run Pike/Winslow seed pipeline synchronously via ReClaw Gateway."""
    qs = f"county={county}&area={area}&write_obsidian={'true' if write_obsidian else 'false'}"
    return _curl_json("POST", f"/run-sync?{qs}")


@mcp.tool()
def rag_vault_sync() -> str:
    """Re-index Obsidian vault into local RAG vector store."""
    return _curl_json("POST", "/rag/vault/sync", timeout=600)


@mcp.tool()
def trigger_county_job(county: str = "Pike", area: str = "Winslow") -> str:
    """Queue background rural_data job (requires gateway token if configured)."""
    return _curl_json("POST", f"/trigger/{county}?area={area}")


@mcp.tool()
def list_recent_sessions(limit: int = 5) -> str:
    """List recent isolated session directories for audit."""
    sessions = ROOT / "data" / "sessions"
    if not sessions.exists():
        return "no sessions dir"
    dirs = sorted(sessions.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    return "\n".join(d.name for d in dirs[:limit])


def _safe_session_id(session_id: str) -> str | None:
    sid = (session_id or "").strip()
    if not sid or len(sid) > 128:
        return None
    if any(c in sid for c in ("/", "\\", "..", "\0", "?", "#", "&")):
        return None
    if not all(c.isalnum() or c in "-_" for c in sid):
        return None
    return sid


@mcp.tool()
def inspect_session(session_id: str = "") -> str:
    """Distilled session audit via gateway. Empty session_id = latest. No full handoff dumps."""
    raw_sid = (session_id or "").strip()
    if raw_sid:
        sid = _safe_session_id(raw_sid)
        if not sid:
            return "invalid session_id (use alphanumeric, dash, underscore only)"
    else:
        listed = _curl_json("GET", "/sessions?limit=1")
        try:
            items = json.loads(listed).get("sessions") or []
            if not items:
                return "no sessions"
            sid = _safe_session_id(items[0].get("session_id", ""))
        except (json.JSONDecodeError, IndexError, TypeError, AttributeError):
            return listed[:500]
        if not sid:
            return "invalid session_id from list"

    raw = _curl_json("GET", f"/sessions/{sid}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:2000]

    handoffs = data.get("handoffs") or {}
    summary = {
        "session_id": data.get("session_id"),
        "has_task": data.get("has_task"),
        "handoff_count": len(handoffs),
        "handoffs": {
            name: {
                "keys": sorted(payload.keys())[:20] if isinstance(payload, dict) else [],
                "status": (payload.get("status") or payload.get("result_status"))
                if isinstance(payload, dict)
                else None,
            }
            for name, payload in handoffs.items()
        },
    }
    ap_raw = _curl_json("GET", f"/sessions/{sid}/approvals")
    try:
        ap = json.loads(ap_raw)
        summary["approvals"] = {
            "pending": len(ap.get("pending") or []),
            "grants": len(ap.get("grants") or []),
        }
    except json.JSONDecodeError:
        pass
    return json.dumps(summary, indent=2)


@mcp.tool()
def pipeline_status() -> str:
    """Distilled pipeline snapshot: health, county queue, packages, recent sessions."""
    out: dict = {}
    for key, path in (
        ("api", "/health"),
        ("county_queue", "/county-queue/status"),
        ("latest_job", "/jobs/latest"),
        ("packages", "/packages?limit=5"),
        ("sessions", "/sessions?limit=5"),
    ):
        raw = _curl_json("GET", path)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            out[key] = raw[:300]
            continue
        if key == "api":
            out[key] = {"status": data.get("status"), "version": data.get("version"), "rag": data.get("rag")}
        elif key == "county_queue":
            cur = data.get("current_county") or {}
            pending = data.get("pending_review") or {}
            out[key] = {
                "status": data.get("queue_status"),
                "cursor": data.get("cursor"),
                "total_counties": data.get("total_counties"),
                "current": cur.get("name"),
                "pending_review": {
                    "county": pending.get("county"),
                    "status": pending.get("status"),
                    "risk_score": pending.get("risk_score"),
                    "flag_count": pending.get("flag_count"),
                    "top_finding": (pending.get("top_finding") or "")[:160],
                }
                if pending
                else None,
            }
        elif key == "packages":
            out["recent_packages"] = data.get("packages") or data
        elif key == "sessions":
            out["recent_sessions"] = [x.get("session_id") for x in (data.get("sessions") or [])]
        else:
            out[key] = data
    return json.dumps(out, indent=2)


@mcp.tool()
def project_sitrep() -> str:
    """FULL ReClaw/Ravenstack live status (docker, Tailscale, OpenClaw, MCP, pipeline, git, vault, gaps)."""
    # Reuse platform implementation (single source of truth)
    import importlib.util

    path = ROOT / "scripts" / "reclaw_platform_mcp_server.py"
    spec = importlib.util.spec_from_file_location("reclaw_platform_mcp_server", path)
    if spec is None or spec.loader is None:
        return "could not load platform sitrep"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.project_sitrep()


@mcp.tool()
def connector_info() -> str:
    """How to attach Grok Build, Gemini, or other MCP clients to this server."""
    return """Ravenstack MCP connector (stdio — runs on Hetzner)

Grok Build (already on server):
  ~/.grok/config.toml → [mcp_servers.ravenstack]
  Restart grok session; tools appear as ravenstack__*

Gemini / other remote MCP clients:
  1. SSH to server: ssh root@178.156.235.36
  2. Run stdio bridge over SSH (from your PC):
     ssh root@178.156.235.36 '/root/ReClaw-2.0/.venv/bin/python /root/ReClaw-2.0/scripts/ravenstack_mcp_server.py'
  3. Point your MCP client at that command (Claude Desktop, Gemini CLI, etc.)

Tailscale (preferred remote path):
  Same SSH command over tailnet hostname openclaw.tail20a090.ts.net

Mutations: ingest_document, save_to_vault, run_rural_data, trigger_county_job
Reads: project_sitrep (FULL status), query_knowledge, read_oracle, stack_health,
       inspect_session, pipeline_status, list_recent_sessions

Chat: "use ravenstack-sitrep" or "use ravenstack connector to project_sitrep"

Env: RECLAW_GATEWAY_URL, RECLAW_GATEWAY_TOKEN, RECLAW_OBSIDIAN_VAULT_PATH
"""


if __name__ == "__main__":
    mcp.run()
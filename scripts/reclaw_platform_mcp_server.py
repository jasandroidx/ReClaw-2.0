#!/usr/bin/env python3
"""ReClaw Platform MCP — unified connector (SuperGrok-style).

One connector for Ravenstack + ReClaw + vault + stack ops. Use from:
  - Grok Build (stdio): tools named reclaw-platform__*
  - Remote clients (HTTP): MCP_TRANSPORT=streamable-http on :8100 via Tailscale

Run stdio (default):
  python scripts/reclaw_platform_mcp_server.py

Run HTTP bridge (tailnet only):
  MCP_TRANSPORT=streamable-http FASTMCP_PORT=8100 python scripts/reclaw_platform_mcp_server.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = Path(os.environ.get("RECLAW_OBSIDIAN_VAULT_PATH", "/root/obsidian_vault"))
sys.path.insert(0, str(ROOT))
os.environ.setdefault("RECLAW_KNOWLEDGE_PATH", str(VAULT / "Ravenstack"))
os.environ.setdefault("RECLAW_OBSIDIAN_VAULT_PATH", str(VAULT))

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from core.config import get_settings
from core.knowledge import KnowledgeManager

_TSNET_HOST = os.environ.get("TAILSCALE_HOST", "openclaw.tail20a090.ts.net")
_TS_IP = os.environ.get("TAILSCALE_IP", "100.108.130.82")
_extra_hosts = [h.strip() for h in os.environ.get("MCP_EXTRA_ALLOWED_HOSTS", "").split(",") if h.strip()]
_public_mode = os.environ.get("MCP_PUBLIC_MODE", "").lower() in ("1", "true", "yes")
_port = int(os.environ.get("FASTMCP_PORT", "8100"))
mcp = FastMCP(
    "reclaw-platform",
    instructions=(
        "You are connected LIVE to the user's ReClaw server via this MCP connector. "
        "THIS chat can call tools and get results immediately. "
        "FORBIDDEN: telling the user to open Grok Build, paste into Build, SSH, or run terminal "
        "commands for anything these tools can do. That is wrong and frustrates the user. "
        "STATUS: call project_sitrep or sitrep (plain-English full report) — show it. "
        "OPERATOR GUIDE: call connector_guide (no args) — show the full document so they can save/copy. "
        "Also: pipeline_status, inspect_session, query_knowledge, read_oracle, read_vault_file, "
        "docker_status, openclaw_health, git_status, stack_health. "
        "Truth + provenance only. Prefer reads; writes/pipeline only if user clearly asks."
    ),
    # Option 2: clients hit this host's Tailscale IP directly.
    host=os.environ.get("FASTMCP_HOST", _TS_IP),
    port=_port,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=not _public_mode,
        allowed_hosts=[
            "127.0.0.1:8100",
            "localhost:8100",
            f"{_TS_IP}:{_port}",
            _TS_IP,
            _TSNET_HOST,
            f"{_TSNET_HOST}:443",
            f"{_TSNET_HOST}:{_port}",
            *_extra_hosts,
        ],
    ),
)
GATEWAY = os.environ.get("RECLAW_GATEWAY_URL", "http://127.0.0.1:8000")
OPENCLAW = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")


def _gateway_token() -> str:
    """Resolve gateway token at call time (env may load after process start)."""
    tok = os.environ.get("RECLAW_GATEWAY_TOKEN", "").strip()
    if tok and tok != "${RECLAW_GATEWAY_TOKEN}":
        return tok
    # bridge script sources /root/.env — also try common env file once
    for path in (Path("/root/.env"), ROOT / ".env"):
        try:
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("RECLAW_GATEWAY_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            continue
    return ""


@mcp.custom_route("/health", methods=["GET"], name="health")
async def health_check(request):  # type: ignore[no-untyped-def]
    """Simple liveness for Tailscale / load checks (not MCP protocol)."""
    from starlette.responses import JSONResponse

    return JSONResponse(
        {
            "status": "ok",
            "service": "reclaw-platform",
            "transport": os.environ.get("MCP_TRANSPORT", "stdio"),
            "port": _port,
        }
    )


def _km() -> KnowledgeManager:
    return KnowledgeManager(get_settings())


def _safe_path(base: Path, rel: str) -> Path:
    p = (base / rel).resolve()
    if not str(p).startswith(str(base.resolve())):
        raise ValueError(f"path escapes sandbox: {rel}")
    return p


def _curl(url: str, method: str = "GET", body: dict | None = None, timeout: int = 120) -> str:
    cmd = ["curl", "-sf", "-X", method, url]
    token = _gateway_token()
    if token and ("127.0.0.1:8000" in url or GATEWAY.rstrip("/") in url.rstrip("/")):
        cmd.extend(["-H", f"Authorization: Bearer {token}"])
    if body is not None:
        cmd.extend(["-H", "Content-Type: application/json", "-d", json.dumps(body)])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        return f"request failed: {proc.stderr or proc.stdout}"
    return proc.stdout


def _curl_json(method: str, path: str, body: dict | None = None, timeout: int = 120) -> str:
    """Gateway JSON helper (same pattern as ravenstack_mcp_server)."""
    raw = _curl(f"{GATEWAY}{path}", method=method, body=body, timeout=timeout)
    if raw.startswith("request failed:"):
        return raw
    try:
        return json.dumps(json.loads(raw), indent=2)
    except json.JSONDecodeError:
        return raw


def _safe_session_id(session_id: str) -> str | None:
    sid = (session_id or "").strip()
    if not sid or len(sid) > 128:
        return None
    # prevent path traversal / injection into URL or FS
    if any(c in sid for c in ("/", "\\", "..", "\0", "?", "#", "&")):
        return None
    if not all(c.isalnum() or c in "-_" for c in sid):
        return None
    return sid


def _distill_session(data: dict) -> dict:
    """Compact session view — no full handoff bodies."""
    handoffs = data.get("handoffs") or {}
    handoff_summary = {}
    for name, payload in handoffs.items():
        if not isinstance(payload, dict):
            handoff_summary[name] = {"type": type(payload).__name__}
            continue
        handoff_summary[name] = {
            "keys": sorted(payload.keys())[:20],
            "status": payload.get("status") or payload.get("result_status"),
        }
    out: dict = {
        "session_id": data.get("session_id"),
        "has_task": data.get("has_task"),
        "handoffs": handoff_summary,
        "handoff_count": len(handoff_summary),
    }
    return out


# --- Ravenstack / knowledge ---


@mcp.tool()
def query_knowledge(query: str, top_k: int = 5) -> str:
    """Semantic search over Obsidian vault + Ravenstack with citations."""
    try:
        from rag.client import RAGClient

        client = RAGClient()
        response = client.search(query=query, top_k=top_k, vault_only=True, min_score=0.25)
        lines = []
        for r in response.results:
            c = r.chunk.citation
            lines.append(
                f"[{r.score:.2f}] {r.chunk.text[:500]}\n  → {c.source_path} ({c.section_header or '-'})"
            )
        return "\n\n".join(lines) if lines else "no matches"
    except Exception as e:
        return f"RAG unavailable ({e}). Index: {_km().get('knowledge_index.md')[:1200]}"


@mcp.tool()
def read_oracle(section: str = "") -> str:
    """Read RAVENSTACK-ORACLE.md (optionally one section by heading)."""
    if section:
        sec = _km().get_section("RAVENSTACK-ORACLE.md", section)
        return f"## {sec.title}\n\n{sec.content}"
    return _km().get("RAVENSTACK-ORACLE.md")[:12000]


@mcp.tool()
def list_knowledge_topics() -> str:
    """List markdown files under Ravenstack knowledge base."""
    kp = _km().knowledge_path
    files = sorted(p.relative_to(kp).as_posix() for p in kp.rglob("*.md"))
    return "\n".join(files[:100])


@mcp.tool()
def ingest_to_ravenstack(source: str, content_or_path: str) -> str:
    """Ingest distilled content into Ravenstack backlog (ORACLE rules)."""
    return str(_km().ingest_document(source, content_or_path, auto_categorize=True))


@mcp.tool()
def save_ravenstack_note(source: str, distilled: str, potential_for: str = "revenue-loops") -> str:
    """Write a distilled note to Ravenstack backlog with frontmatter."""
    return str(_km().save_to_backlog(source, distilled, potential_for))


# --- Vault read/write (real-time) ---


@mcp.tool()
def read_vault_file(relative_path: str, max_chars: int = 12000) -> str:
    """Read a vault file NOW and return its text in this chat (no Grok Build, no paste).

    relative_path is under the Obsidian vault, e.g. Ravenstack/super-grok-connector-guide.md
    or Rural Data/_latest.md. Show the content to the user so they can copy/save.
    """
    p = _safe_path(VAULT, relative_path)
    if not p.exists():
        return f"not found: {relative_path}"
    return p.read_text(encoding="utf-8", errors="replace")[:max_chars]


@mcp.tool()
def connector_guide() -> str:
    """Show the SuperGrok × ReClaw operator guide in THIS chat (full document).

    Call with no arguments when the user wants the connector guide, operator manual,
    how to use tools, killer combos, or how to add GitHub. Return the full markdown
    so they can copy/save to phone or computer. Do NOT redirect to Grok Build.
    """
    path = VAULT / "Ravenstack" / "super-grok-connector-guide.md"
    if not path.is_file():
        # fallback to repo mirror
        alt = ROOT / "docs" / "SUPER-GROK-CONNECTOR-GUIDE.md"
        if alt.is_file():
            return alt.read_text(encoding="utf-8", errors="replace")[:50000]
        return "Guide not found on server. Ask Build once to recreate Ravenstack/super-grok-connector-guide.md"
    return path.read_text(encoding="utf-8", errors="replace")[:50000]


@mcp.tool()
def write_vault_file(relative_path: str, content: str) -> str:
    """Write or update a file under the Obsidian vault. Creates parent dirs."""
    p = _safe_path(VAULT, relative_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} chars → {p}"


@mcp.tool()
def read_repo_file(relative_path: str, max_chars: int = 12000) -> str:
    """Read a file under /root/ReClaw-2.0 (code, config, skills)."""
    p = _safe_path(ROOT, relative_path)
    if not p.exists():
        return f"not found: {relative_path}"
    return p.read_text(encoding="utf-8", errors="replace")[:max_chars]


# --- ReClaw pipeline ---


@mcp.tool()
def reclaw_health() -> str:
    """ReClaw API gateway health JSON."""
    return _curl(f"{GATEWAY}/health")


@mcp.tool()
def run_pike_winslow(county: str = "Pike", area: str = "Winslow", write_obsidian: bool = True) -> str:
    """Run rural_data seed pipeline (Researcher → Analyst → Obsidian package)."""
    qs = f"county={county}&area={area}&write_obsidian={'true' if write_obsidian else 'false'}"
    return _curl(f"{GATEWAY}/run-sync?{qs}", method="POST", timeout=300)


@mcp.tool()
def rag_sync_vault() -> str:
    """Re-index full Obsidian vault into RAG vector store."""
    return _curl(f"{GATEWAY}/rag/vault/sync", method="POST", timeout=600)


@mcp.tool()
def list_pipeline_sessions(limit: int = 8) -> str:
    """List recent isolated pipeline session folders."""
    sessions = ROOT / "data" / "sessions"
    if not sessions.exists():
        return "no sessions"
    dirs = sorted(sessions.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    return "\n".join(d.name for d in dirs[:limit])


@mcp.tool()
def inspect_session(session_id: str = "") -> str:
    """Distilled session audit: handoff names/status, task flag, approvals. No raw handoff dumps."""
    raw_sid = (session_id or "").strip()
    if raw_sid:
        sid = _safe_session_id(raw_sid)
        if not sid:
            return "invalid session_id (use alphanumeric, dash, underscore only)"
    else:
        # default: most recent session from gateway
        raw = _curl(f"{GATEWAY}/sessions?limit=1")
        if raw.startswith("request failed:"):
            return raw
        try:
            items = json.loads(raw).get("sessions") or []
            if not items:
                return "no sessions"
            sid = _safe_session_id(items[0].get("session_id", ""))
        except (json.JSONDecodeError, IndexError, TypeError):
            return "could not resolve latest session"
        if not sid:
            return "invalid session_id from list"

    raw = _curl(f"{GATEWAY}/sessions/{sid}")
    if raw.startswith("request failed:"):
        return raw
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:2000]

    distilled = _distill_session(data)

    # optional task peek (disk, sandboxed)
    task_path = ROOT / "data" / "sessions" / sid / "task.json"
    if task_path.is_file():
        try:
            task = json.loads(task_path.read_text(encoding="utf-8", errors="replace")[:8000])
            distilled["task"] = {
                k: task.get(k)
                for k in ("county", "area", "primary_area", "goal", "status", "domain")
                if k in task
            }
        except (json.JSONDecodeError, OSError):
            distilled["task"] = {"error": "unreadable"}

    approvals_raw = _curl(f"{GATEWAY}/sessions/{sid}/approvals")
    if not approvals_raw.startswith("request failed:"):
        try:
            ap = json.loads(approvals_raw)
            distilled["approvals"] = {
                "pending": len(ap.get("pending") or []),
                "grants": len(ap.get("grants") or []),
            }
        except json.JSONDecodeError:
            pass

    return json.dumps(distilled, indent=2)


@mcp.tool()
def pipeline_status() -> str:
    """Distilled pipeline snapshot: health, county queue, latest job/packages, recent sessions."""
    out: dict = {}

    health_raw = _curl(f"{GATEWAY}/health")
    try:
        h = json.loads(health_raw)
        out["api"] = {"status": h.get("status"), "version": h.get("version"), "rag": h.get("rag")}
    except json.JSONDecodeError:
        out["api"] = health_raw[:200] if not health_raw.startswith("request failed:") else health_raw

    queue_raw = _curl(f"{GATEWAY}/county-queue/status")
    if not queue_raw.startswith("request failed:"):
        try:
            q = json.loads(queue_raw)
            cur = q.get("current_county") or {}
            pending = q.get("pending_review") or {}
            out["county_queue"] = {
                "status": q.get("queue_status"),
                "cursor": q.get("cursor"),
                "total_counties": q.get("total_counties"),
                "current": cur.get("name") or cur.get("gateway_code"),
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
        except json.JSONDecodeError:
            out["county_queue"] = "parse_error"

    latest_raw = _curl(f"{GATEWAY}/jobs/latest")
    if not latest_raw.startswith("request failed:"):
        try:
            out["latest_job"] = json.loads(latest_raw)
        except json.JSONDecodeError:
            out["latest_job"] = latest_raw[:300]

    pkgs_raw = _curl(f"{GATEWAY}/packages?limit=5")
    if not pkgs_raw.startswith("request failed:"):
        try:
            pkgs = json.loads(pkgs_raw)
            out["recent_packages"] = pkgs.get("packages") or pkgs
        except json.JSONDecodeError:
            out["recent_packages"] = "parse_error"

    sess_raw = _curl(f"{GATEWAY}/sessions?limit=5")
    if not sess_raw.startswith("request failed:"):
        try:
            s = json.loads(sess_raw)
            out["recent_sessions"] = [x.get("session_id") for x in (s.get("sessions") or [])]
        except json.JSONDecodeError:
            out["recent_sessions"] = []

    return json.dumps(out, indent=2)


# --- Stack ops ---


@mcp.tool()
def stack_health() -> str:
    """Docker + API + gateway + Ollama post-deploy healthcheck."""
    script = ROOT / "scripts" / "post-deploy-healthcheck.sh"
    proc = subprocess.run(["bash", str(script)], cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    return (proc.stdout or "") + (proc.stderr or "")


@mcp.tool()
def docker_status() -> str:
    """docker compose ps for ReClaw stack."""
    proc = subprocess.run(
        ["docker", "compose", "ps"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.stdout or proc.stderr


@mcp.tool()
def openclaw_health() -> str:
    """OpenClaw gateway health."""
    return _curl(f"{OPENCLAW}/health")


@mcp.tool()
def git_status() -> str:
    """Git branch and short status for ReClaw-2.0 repo."""
    proc = subprocess.run(
        ["git", "status", "-sb"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=15,
    )
    return proc.stdout or proc.stderr


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 30) -> str:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return ((proc.stdout or "") + (proc.stderr or "")).strip()
    except Exception as e:
        return f"error: {e}"


def _fmt_overall(overall: str) -> str:
    return {
        "healthy": "🟢 HEALTHY",
        "healthy_with_gaps": "🟡 HEALTHY WITH GAPS",
        "degraded": "🟡 DEGRADED",
        "down": "🔴 DOWN",
    }.get(overall, overall.upper())


def _format_sitrep_plain(report: dict) -> str:
    """Human-readable full sitrep — what the Grok app should show the user."""
    lines: list[str] = []
    overall = report.get("overall", "unknown")
    as_of = report.get("as_of", "?")
    gaps = report.get("gaps") or []
    lines.append("# Ravenstack Sitrep — Full Project Status")
    lines.append(f"**As of:** {as_of} UTC · **Overall:** {_fmt_overall(str(overall))}")
    lines.append("")
    lines.append("## 1. Executive summary")
    if overall == "healthy":
        lines.append("The fortress is fully up. No critical blockers detected.")
    elif overall == "healthy_with_gaps":
        lines.append(
            "Core services are up, but there are operational gaps that need attention "
            f"({len(gaps)} item(s) below). Nothing looks fully offline."
        )
    elif overall == "degraded":
        lines.append(
            "Some services are unhealthy or offline. Review Blockers and fix the highest severity first."
        )
    else:
        lines.append(
            "Critical path looks down (API and/or OpenClaw). Treat this as an outage until verified green."
        )
    if gaps:
        lines.append("Top issues: " + "; ".join(gaps[:3]) + ("…" if len(gaps) > 3 else "") + ".")
    lines.append("")

    # Docker
    lines.append("## 2. Docker compose")
    docker = report.get("docker") or {}
    services = docker.get("services") or []
    if not services:
        lines.append("- No services reported (docker probe failed or empty).")
    else:
        lines.append(f"- **{docker.get('count', len(services))}** compose service(s):")
        for s in services:
            if "raw" in s:
                lines.append(f"- Raw: {str(s['raw'])[:200]}")
                continue
            name = s.get("name") or s.get("service") or "?"
            state = s.get("state") or "?"
            health = s.get("health") or "n/a"
            ports = s.get("ports") or ""
            if isinstance(ports, list):
                ports = json.dumps(ports)[:80]
            lines.append(f"- **{name}**: {state}" + (f" · health={health}" if health else "") + (f" · {ports}" if ports else ""))
    lines.append("")

    # API
    lines.append("## 3. ReClaw API (Gateway)")
    api = report.get("reclaw_api") or {}
    if isinstance(api, dict):
        lines.append(f"- Status: **{api.get('status', '?')}** · version: {api.get('version', '?')}")
        if api.get("rag"):
            lines.append(f"- RAG: {api.get('rag')}")
        if api.get("detail"):
            lines.append(f"- Detail: {api.get('detail')}")
    else:
        lines.append(f"- {api}")
    lines.append("")

    # OpenClaw
    lines.append("## 4. OpenClaw gateway (Docker)")
    oc = report.get("openclaw_gateway") or {}
    if isinstance(oc, dict):
        ok = oc.get("ok")
        st = oc.get("status") or oc.get("detail") or "?"
        lines.append(f"- Health: **{'ok' if ok else st}** (status={st})")
    else:
        lines.append(f"- {oc}")
    lines.append(f"- Single-gateway guard: {report.get('openclaw_single_gateway', '?')}")
    lines.append("- Port: **18789** (compose service openclaw-gateway)")
    lines.append("")

    # Tailscale
    lines.append("## 5. Tailscale")
    ts = report.get("tailscale") or {}
    lines.append(f"- IP: **{ts.get('ip') or 'unknown'}**")
    serve = (ts.get("serve") or "").strip()
    if serve:
        # keep short
        for ln in serve.splitlines()[:8]:
            lines.append(f"- Serve: `{ln.strip()}`")
    else:
        lines.append("- Serve: (no status)")
    lines.append("")

    # MCP
    lines.append("## 6. MCP connector")
    mcp = report.get("mcp") or {}
    mh = mcp.get("health") or {}
    lines.append(f"- Bridge (systemd): **{mcp.get('bridge_systemd', '?')}**")
    lines.append(f"- Public tunnel (systemd): **{mcp.get('tunnel_systemd', '?')}**")
    lines.append(
        f"- MCP process: **{mh.get('status', '?')}** · port {mh.get('port', '?')} · "
        f"transport {mh.get('transport', '?')}"
    )
    if mcp.get("public_url_file"):
        lines.append(f"- Public connector URL file: `{mcp.get('public_url_file')}`")
    if mcp.get("public_health_http"):
        lines.append(f"- Public health HTTP: {mcp.get('public_health_http')}")
    lines.append("- This report was produced **in-chat** by the connector (no paste to Grok Build needed).")
    lines.append("")

    # Ollama
    lines.append("## 7. LLM / Ollama")
    ol = report.get("ollama") or {}
    lines.append(f"- Status: **{ol.get('status', '?')}** · models: {ol.get('models', '?')}")
    if ol.get("detail"):
        lines.append(f"- Detail: {ol.get('detail')}")
    lines.append("")

    # Dashboard
    lines.append("## 8. Fortress dashboard")
    dash = report.get("fortress_dashboard") or {}
    lines.append(f"- :8081 → HTTP **{dash.get('http', '?')}** · **{dash.get('status', '?')}**")
    lines.append("")

    # Pipeline
    lines.append("## 9. Pipeline & county queue")
    pipe = report.get("pipeline") or {}
    if pipe.get("error"):
        lines.append(f"- Pipeline probe error: {pipe.get('error')}")
    else:
        cq = pipe.get("county_queue") or {}
        lines.append(
            f"- Queue: **{cq.get('status', '?')}** · cursor {cq.get('cursor', '?')}/"
            f"{cq.get('total_counties', '?')} · current county: **{cq.get('current', '?')}**"
        )
        pr = cq.get("pending_review") or {}
        if pr:
            lines.append(
                f"- Pending review: **{pr.get('county')}** · risk {pr.get('risk_score')} · "
                f"flags {pr.get('flag_count')} · {pr.get('status')}"
            )
            if pr.get("top_finding"):
                lines.append(f"- Top finding: {pr.get('top_finding')}")
        pkgs = pipe.get("recent_packages") or []
        if pkgs:
            lines.append("- Recent packages:")
            for p in pkgs[:5]:
                if isinstance(p, dict):
                    lines.append(
                        f"  - {p.get('county')}/{p.get('area')}: risk {p.get('risk')} · "
                        f"flags {p.get('flags')} · {p.get('generated_at', '')[:19]}"
                    )
        sess = pipe.get("recent_sessions") or []
        if sess:
            lines.append("- Recent sessions: " + ", ".join(str(s) for s in sess[:5]))
        api_p = pipe.get("api") or {}
        if api_p:
            lines.append(f"- API (from pipeline): {api_p.get('status')} v{api_p.get('version', '?')}")
    ls = report.get("latest_session") or {}
    if ls and not ls.get("error"):
        lines.append(
            f"- Latest session **{ls.get('session_id')}**: handoffs={ls.get('handoff_count')} "
            f"({', '.join((ls.get('handoffs') or {}).keys())}) · "
            f"approvals pending={((ls.get('approvals') or {}).get('pending'))} "
            f"grants={((ls.get('approvals') or {}).get('grants'))}"
        )
        task = ls.get("task") or {}
        if task:
            lines.append(
                f"- Task: county={task.get('county') or task.get('primary_area')} "
                f"area={task.get('primary_area') or task.get('area')}"
            )
    elif ls.get("error"):
        lines.append(f"- Latest session: {ls.get('error')}")
    lines.append("")

    # Git reclaw
    lines.append("## 10. Git — ReClaw repo")
    gr = (report.get("git") or {}).get("reclaw") or {}
    branch_line = gr.get("sync_note") or (
        gr.get("status_sb", "").splitlines()[0] if gr.get("status_sb") else "?"
    )
    lines.append(f"- Branch line: `{branch_line}`")
    lines.append(f"- Dirty (uncommitted): **{'yes' if gr.get('dirty') else 'no'}**")
    lines.append(f"- HEAD: {gr.get('head') or '?'}")
    lines.append(f"- Remote: {gr.get('remote') or '?'}")
    lines.append("")

    # GitHub
    lines.append("## 11. GitHub")
    gh = report.get("github") or {}
    if isinstance(gh, dict) and gh.get("url"):
        br = (gh.get("defaultBranchRef") or {}).get("name") if isinstance(gh.get("defaultBranchRef"), dict) else "?"
        lines.append(
            f"- **{gh.get('name')}** · {gh.get('url')} · default branch `{br}` · "
            f"private={gh.get('isPrivate')} · updated {gh.get('updatedAt')}"
        )
    else:
        lines.append(f"- {gh.get('detail') if isinstance(gh, dict) else gh}")
    lines.append("")

    # Obsidian
    lines.append("## 12. Obsidian vault")
    ob = report.get("obsidian") or {}
    lines.append(f"- Path: `{ob.get('vault_path')}`")
    lines.append(
        f"- Ravenstack notes: **{ob.get('ravenstack_md_count')}** · ORACLE: "
        f"{'yes' if ob.get('oracle_present') else 'NO'} · mcp-connector.md: "
        f"{'yes' if ob.get('mcp_connector_doc') else 'NO'}"
    )
    lines.append(f"- Rural Data markdown files: **{ob.get('rural_data_md_count')}**")
    if ob.get("rural_latest_preview"):
        lines.append(f"- _latest preview: {ob.get('rural_latest_preview')}")
    gv = (report.get("git") or {}).get("obsidian_vault") or {}
    lines.append(f"- Vault git dirty: **{'yes' if gv.get('dirty') else 'no'}** · `{gv.get('sync_note') or ''}`")
    lines.append("")

    # RAG
    lines.append("## 13. Knowledge / RAG")
    rag = report.get("rag") or {}
    lines.append(f"- RAG: **{rag.get('status', '?')}** · hits: {rag.get('hits', '?')}")
    if rag.get("detail"):
        lines.append(f"- Detail: {rag.get('detail')}")
    lines.append(
        f"- Anchors: ORACLE={'yes' if ob.get('oracle_present') else 'no'}, "
        f"mcp-connector={'yes' if ob.get('mcp_connector_doc') else 'no'}"
    )
    lines.append("")

    # Gaps
    lines.append("## 14. Blockers & gaps")
    if not gaps:
        lines.append("- none")
    else:
        for g in gaps:
            sev = "high" if any(x in g.lower() for x in ("down", "unhealthy", "inactive", "failed")) else "medium"
            lines.append(f"- **{sev}** · {g}")
    lines.append("")

    # Next
    lines.append("## 15. Next actions")
    hints = report.get("next_actions_hint") or gaps[:5] or ["No action required."]
    for i, h in enumerate(hints[:5], 1):
        lines.append(f"{i}. {h}")
    lines.append("")

    lines.append("## 16. Provenance")
    lines.append("- Source: live `project_sitrep` on reclaw-platform MCP (this server)")
    lines.append("- Format: plain-English full report (not raw JSON)")
    lines.append("- Read-only: no pipeline run, no vault writes, no approvals")
    lines.append("")
    lines.append(
        "_Show this report to the user as-is (you may lightly rephrase). "
        "Do not ask them to paste into Grok Build or re-run tools unless something failed._"
    )
    return "\n".join(lines)


@mcp.tool()
def project_sitrep() -> str:
    """FULL live fortress status report in PLAIN ENGLISH — ready to show the user.

    Returns a complete markdown sitrep (every section summarized). Call with no arguments.
    Do NOT ask the user to paste into Grok Build. Do NOT return only JSON.
    Covers Docker, API, OpenClaw, Tailscale, MCP, Ollama, dashboard, county queue,
    sessions, git, GitHub, Obsidian, RAG, gaps, next actions. Read-only.
    Triggers: project sitrep, sitrep, full status, fortress status, health everything.
    """
    from datetime import datetime, timezone

    report: dict = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool": "project_sitrep",
    }
    gaps: list[str] = []

    # --- Docker ---
    docker = _run(["docker", "compose", "ps", "--format", "json"], timeout=30)
    services: list[dict] = []
    if docker and not docker.startswith("error:"):
        # docker compose may emit NDJSON or array
        try:
            if docker.strip().startswith("["):
                rows = json.loads(docker)
            else:
                rows = [json.loads(line) for line in docker.splitlines() if line.strip().startswith("{")]
            for r in rows:
                services.append(
                    {
                        "name": r.get("Name") or r.get("Service"),
                        "service": r.get("Service"),
                        "state": r.get("State") or r.get("Status"),
                        "health": r.get("Health") or "",
                        "ports": r.get("Publishers") or r.get("Ports") or "",
                    }
                )
        except json.JSONDecodeError:
            services = [{"raw": docker[:800]}]
    else:
        gaps.append("docker compose ps failed")
    report["docker"] = {"services": services, "count": len(services)}

    # --- Core HTTP health ---
    def _jget(url: str) -> dict | str:
        raw = _curl(url, timeout=15)
        if raw.startswith("request failed:"):
            return raw
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw[:300]

    api_h = _jget(f"{GATEWAY}/health")
    oc_h = _jget(f"{OPENCLAW}/health")
    report["reclaw_api"] = api_h if isinstance(api_h, dict) else {"status": "down", "detail": str(api_h)[:200]}
    report["openclaw_gateway"] = oc_h if isinstance(oc_h, dict) else {"status": "down", "detail": str(oc_h)[:200]}
    if isinstance(api_h, str) or (isinstance(api_h, dict) and api_h.get("status") not in ("ok", "healthy")):
        gaps.append("ReClaw API unhealthy")
    if isinstance(oc_h, str) or (isinstance(oc_h, dict) and not (oc_h.get("ok") or oc_h.get("status") in ("live", "ok"))):
        gaps.append("OpenClaw gateway unhealthy")

    # Single-gateway guard
    guard = _run(["bash", str(ROOT / "scripts" / "ensure-single-openclaw.sh")], timeout=30)
    report["openclaw_single_gateway"] = "ok" if "healthy" in guard.lower() or "canonical" in guard.lower() else guard[:400]
    if "ok" not in report["openclaw_single_gateway"]:
        if "duplicate" in guard.lower() or "failed" in guard.lower():
            gaps.append("OpenClaw gateway guard issue")

    # --- Ollama / dashboard ---
    ollama = _run(
        ["curl", "-sf", "http://127.0.0.1:11434/api/tags"],
        timeout=10,
    )
    try:
        models = json.loads(ollama).get("models") or []
        report["ollama"] = {"status": "up", "models": len(models)}
    except Exception:
        report["ollama"] = {"status": "down_or_unknown", "detail": ollama[:120]}
        gaps.append("Ollama not responding on :11434")

    dash = _run(["curl", "-sf", "-o", "/dev/null", "-w", "%{http_code}", "http://127.0.0.1:8081/"], timeout=10)
    report["fortress_dashboard"] = {"http": dash, "status": "up" if dash == "200" else "down"}
    if dash != "200":
        gaps.append("Fortress dashboard :8081 not 200")

    # --- Tailscale ---
    ts_ip = _run(["tailscale", "ip", "-4"], timeout=10)
    ts_serve = _run(["tailscale", "serve", "status"], timeout=15)
    report["tailscale"] = {
        "ip": ts_ip.splitlines()[0] if ts_ip and not ts_ip.startswith("error:") else None,
        "serve": ts_serve[:600] if ts_serve else None,
    }
    if not report["tailscale"]["ip"]:
        gaps.append("Tailscale IP unavailable")

    # --- MCP bridge + public tunnel ---
    # IMPORTANT: never curl this process's own :8100 while serving tools/call — deadlocks
    # single-worker streamable-http and makes SuperGrok/app "fail" into paste-to-Build advice.
    bridge = _run(["systemctl", "is-active", "reclaw-mcp-bridge"], timeout=5)
    tunnel = _run(["systemctl", "is-active", "reclaw-mcp-tunnel"], timeout=5)
    public_url = ""
    url_file = ROOT / "data" / "mcp_public_url.txt"
    if url_file.is_file():
        public_url = url_file.read_text(encoding="utf-8", errors="replace").strip()
    public_code = ""
    if public_url:
        # Cloudflare path is external; use short timeout. Empty/timeout ≠ bridge down.
        public_code = _run(
            [
                "curl",
                "-sf",
                "--max-time",
                "5",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                public_url.replace("/mcp", "/health"),
            ],
            timeout=8,
        )
    report["mcp"] = {
        "bridge_systemd": bridge,
        "tunnel_systemd": tunnel,
        "health": {
            "status": "ok" if bridge == "active" else "down",
            "note": "serving this project_sitrep request (no self-HTTP probe)",
            "port": _port,
            "transport": os.environ.get("MCP_TRANSPORT", "stdio"),
        },
        "public_url_file": public_url or None,
        "public_health_http": public_code or None,
        "tools_note": "Call project_sitrep or sitrep in THIS chat — do not paste to Grok Build",
    }
    if bridge != "active":
        gaps.append("MCP bridge inactive")
    if tunnel != "active":
        gaps.append("MCP public tunnel inactive")

    # --- Pipeline (reuse distilled logic) ---
    try:
        report["pipeline"] = json.loads(pipeline_status())
        cq = report["pipeline"].get("county_queue") or {}
        if cq.get("status") == "awaiting_approval":
            gaps.append(f"County queue awaiting approval: {cq.get('current') or cq.get('pending_review')}")
    except Exception as e:
        report["pipeline"] = {"error": str(e)}
        gaps.append("pipeline_status failed")

    # --- Latest session ---
    try:
        report["latest_session"] = json.loads(inspect_session(""))
    except Exception as e:
        report["latest_session"] = {"error": str(e)}

    # --- Git: ReClaw + vault ---
    def _git_summary(path: Path) -> dict:
        if not (path / ".git").exists() and not path.exists():
            return {"error": "missing"}
        br = _run(["git", "status", "-sb"], cwd=path, timeout=15)
        rem = _run(["git", "remote", "-v"], cwd=path, timeout=10)
        log = _run(["git", "log", "-1", "--oneline"], cwd=path, timeout=10)
        dirty = any(line.startswith(" M") or line.startswith("??") or line.startswith(" D") for line in br.splitlines()[1:])
        ahead = "ahead" in br or "behind" in br
        return {
            "status_sb": br[:500],
            "remote": rem.splitlines()[0] if rem else None,
            "head": log,
            "dirty": dirty or ("??" in br or " M" in br or " D" in br),
            "sync_note": br.splitlines()[0] if br else None,
            "ahead_behind": ahead,
        }

    report["git"] = {
        "reclaw": _git_summary(ROOT),
        "obsidian_vault": _git_summary(VAULT),
    }
    if report["git"]["reclaw"].get("dirty"):
        gaps.append("ReClaw repo dirty (uncommitted work)")
    if report["git"]["obsidian_vault"].get("dirty"):
        gaps.append("Obsidian vault dirty (uncommitted notes)")

    # --- GitHub (gh, read-only) ---
    gh = _run(
        ["gh", "repo", "view", "jasandroidx/ReClaw-2.0", "--json", "name,defaultBranchRef,updatedAt,isPrivate,url"],
        timeout=20,
    )
    try:
        report["github"] = json.loads(gh)
    except json.JSONDecodeError:
        report["github"] = {"detail": gh[:300]}
        if "error" in gh.lower() or not gh:
            gaps.append("GitHub gh view failed")

    # --- Obsidian / Ravenstack knowledge ---
    kp = VAULT / "Ravenstack"
    topics = sorted(p.relative_to(kp).as_posix() for p in kp.rglob("*.md") if p.is_file()) if kp.is_dir() else []
    oracle_ok = (kp / "RAVENSTACK-ORACLE.md").is_file()
    mcp_doc_ok = (kp / "mcp-connector.md").is_file()
    rural = VAULT / "Rural Data"
    latest_rural = ""
    latest_path = rural / "_latest.md"
    if latest_path.is_file():
        latest_rural = latest_path.read_text(encoding="utf-8", errors="replace")[:300]
    rural_count = len(list(rural.glob("*.md"))) if rural.is_dir() else 0
    report["obsidian"] = {
        "vault_path": str(VAULT),
        "ravenstack_md_count": len(topics),
        "oracle_present": oracle_ok,
        "mcp_connector_doc": mcp_doc_ok,
        "key_topics": [t for t in topics if not t.startswith("mcp-audit/")][:25],
        "rural_data_md_count": rural_count,
        "rural_latest_preview": latest_rural.replace("\n", " ")[:200],
    }
    if not oracle_ok:
        gaps.append("ORACLE missing from vault")
    if not mcp_doc_ok:
        gaps.append("mcp-connector.md missing from vault")

    # --- RAG smoke ---
    rag_raw = _curl(
        f"{GATEWAY}/rag/search",
        method="POST",
        body={"query": "Ravenstack MCP connector", "top_k": 2},
        timeout=30,
    )
    if rag_raw.startswith("request failed:"):
        report["rag"] = {"status": "error", "detail": rag_raw[:200]}
        gaps.append("RAG search failed")
    else:
        try:
            rag = json.loads(rag_raw)
            n = len(rag.get("results") or rag.get("hits") or [])
            report["rag"] = {"status": "ok" if n else "empty", "hits": n}
            if not n:
                gaps.append("RAG returned zero hits (index may be stale)")
        except json.JSONDecodeError:
            report["rag"] = {"status": "unknown", "detail": rag_raw[:200]}

    # --- Overall ---
    api_ok = isinstance(report["reclaw_api"], dict) and report["reclaw_api"].get("status") in ("ok", "healthy")
    oc = report["openclaw_gateway"]
    oc_ok = isinstance(oc, dict) and (oc.get("ok") is True or oc.get("status") in ("live", "ok", "healthy"))
    if not api_ok or not oc_ok:
        overall = "down"
    elif any(x in g.lower() for g in gaps for x in ("inactive", "unhealthy", "failed", "not 200", "not responding")):
        overall = "degraded"
    elif gaps:
        overall = "healthy_with_gaps"
    else:
        overall = "healthy"
    report["overall"] = overall
    report["gaps"] = gaps
    report["next_actions_hint"] = gaps[:5] if gaps else [
        "Stack clear — run daily pipeline or county-queue approve as needed"
    ]

    # Plain English is the product. (JSON was for machines; chat users want the report.)
    return _format_sitrep_plain(report)


@mcp.tool()
def sitrep() -> str:
    """Same as project_sitrep: full plain-English fortress status. Call now; show user the result."""
    return project_sitrep()


@mcp.tool()
def connector_help() -> str:
    """How this connector works — Grok Build, SuperGrok-style remote, Gemini."""
    return f"""ReClaw Platform MCP — unified connector

IMPORTANT FOR GROK APP / SUPERGROK CHAT:
  Call tools HERE. Never say "paste this into Grok Build".
  Full status: call project_sitrep (or sitrep) → plain English report → show the user.
  Operator guide: call connector_guide (no args) → full doc → user can copy/save.
  NEVER say "paste into Grok Build" for tool-backed tasks.

WHAT IT IS (like SuperGrok → GitHub):
  One MCP server exposing tools so the model can SEE and CHANGE your stack in real time.

FULL PROJECT STATUS (chat):
  Tool: project_sitrep  (alias: sitrep)
  Say: "Call project_sitrep and summarize every section"

GROK BUILD (this server — best experience):
  Config: /root/ReClaw-2.0/.grok/config.toml → [mcp_servers.reclaw-platform] stdio
  Tools: reclaw-platform__project_sitrep, __stack_health, __pipeline_status, etc.

REMOTE — Grok.com Connectors (xAI cloud; needs PUBLIC HTTPS, not Tailscale IP):
  URL file: /root/ReClaw-2.0/data/mcp_public_url.txt  (cloudflared quick tunnel; hostnames rotate)
  Refresh:  systemctl restart reclaw-mcp-tunnel
  Path MUST end with /mcp
  Chat: "use ravenstack connector to project_sitrep"

TAILNET only (phone/laptop with Tailscale; NOT grok.com):
  Health: http://{_TS_IP}:8100/health
  MCP:    http://{_TS_IP}:8100/mcp
  Or:     https://openclaw.tail20a090.ts.net/reclaw-mcp/mcp

STDIO over SSH:
  ssh root@178.156.235.36 '{ROOT}/.venv/bin/python {ROOT}/scripts/reclaw_platform_mcp_server.py'

SECURITY: HTTP MCP has no auth — treat public tunnel URL as secret; prefer Tailscale;
  vault/repo path-sandboxed; mutations need explicit user intent. Full map: vault Ravenstack/mcp-connector.md

WRITE TOOLS: write_vault_file, save_ravenstack_note, ingest_to_ravenstack, run_pike_winslow
READ TOOLS: project_sitrep, inspect_session, pipeline_status, read_vault_file, query_knowledge, read_oracle
OPS: stack_health, docker_status, git_status (20 tools total)

Also available separately: ravenstack, reclaw-api, reclaw-fs, obsidian MCPs.
"""


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport not in ("stdio", "sse", "streamable-http"):
        transport = "stdio"
    mcp.run(transport=transport)  # type: ignore[arg-type]
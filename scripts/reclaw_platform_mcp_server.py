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
_extra_hosts = [h.strip() for h in os.environ.get("MCP_EXTRA_ALLOWED_HOSTS", "").split(",") if h.strip()]
_public_mode = os.environ.get("MCP_PUBLIC_MODE", "").lower() in ("1", "true", "yes")
mcp = FastMCP(
    "reclaw-platform",
    instructions=(
        "ReClaw 2.0 + Ravenstack connector. Read ORACLE, search RAG, read/write Obsidian vault, "
        "run Pike/Winslow pipeline, inspect Docker/Tailscale health. Truth + provenance only."
    ),
    host=os.environ.get("FASTMCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("FASTMCP_PORT", "8100")),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=not _public_mode,
        allowed_hosts=[
            "127.0.0.1:8100",
            "localhost:8100",
            _TSNET_HOST,
            f"{_TSNET_HOST}:443",
            *_extra_hosts,
        ],
    ),
)
GATEWAY = os.environ.get("RECLAW_GATEWAY_URL", "http://127.0.0.1:8000")
OPENCLAW = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")
TOKEN = os.environ.get("RECLAW_GATEWAY_TOKEN", "")


def _km() -> KnowledgeManager:
    return KnowledgeManager(get_settings())


def _safe_path(base: Path, rel: str) -> Path:
    p = (base / rel).resolve()
    if not str(p).startswith(str(base.resolve())):
        raise ValueError(f"path escapes sandbox: {rel}")
    return p


def _git(cwd, *args, timeout: int = 15):
    """Run git in cwd. Returns (returncode, stripped stdout)."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, (proc.stdout or "").strip()
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


def _durability(p: Path) -> dict:
    """Is this file actually durable, or does it live on one machine only?

    A write succeeding says nothing about whether the work survives the session.
    This answers the second question so a caller cannot claim durability it
    does not have.
    """
    rc, repo_root = _git(p.parent, "rev-parse", "--show-toplevel")
    if rc != 0 or not repo_root:
        return {
            "git_repo": False,
            "durability": "unknown",
            "committed": False,
            "pushed": False,
            "warning": (
                f"NOT VERSIONED — {p} is not inside a git repo. Durability cannot be "
                "verified. Do not describe this file as saved, shared, backed up, or "
                "cross-session memory."
            ),
        }

    root = Path(repo_root)
    try:
        rel = p.resolve().relative_to(root).as_posix()
    except ValueError:
        rel = p.name

    _, branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    tracked_rc, _ = _git(root, "ls-files", "--error-unmatch", "--", rel)
    _, porcelain = _git(root, "status", "--porcelain", "--", rel)
    committed = tracked_rc == 0 and porcelain == ""

    pushed = False
    upstream = None
    if committed:
        rc_up, up = _git(root, "rev-parse", "--abbrev-ref", "@{u}")
        if rc_up == 0 and up:
            upstream = up
            rc_sha, sha = _git(root, "log", "-1", "--format=%H", "--", rel)
            if rc_sha == 0 and sha:
                rc_anc, _ = _git(root, "merge-base", "--is-ancestor", sha, upstream)
                pushed = rc_anc == 0

    _, all_dirty = _git(root, "status", "--porcelain")
    dirty_count = len([ln for ln in all_dirty.splitlines() if ln.strip()])

    if pushed:
        durability, warning = "pushed", None
    elif committed:
        durability = "committed-not-pushed"
        warning = (
            f"PARTIALLY DURABLE — committed to '{branch}' on this machine but not on "
            f"the remote{f' ({upstream})' if upstream else ''}. It survives a restart, "
            "not a lost box, and no other clone can see it. Push before calling it shared."
        )
    else:
        durability = "local-only"
        warning = (
            f"NOT DURABLE — this file exists only at {p} and is uncommitted on branch "
            f"'{branch}'. Any session that clones the repo cannot see it. Do NOT describe "
            "it as saved, shared, backed up, or cross-session memory until it is committed "
            "and pushed."
        )

    out = {
        "git_repo": True,
        "repo": str(root),
        "branch": branch,
        "upstream": upstream,
        "committed": committed,
        "pushed": pushed,
        "durability": durability,
        "repo_uncommitted_files": dirty_count,
    }
    if warning:
        out["warning"] = warning
    if committed and upstream:
        out["note"] = (
            "'pushed' is measured against the local remote-tracking ref, which reflects "
            "the last fetch. Fetch first if the answer must be current."
        )
    return out


def _receipt(p: Path, base: Path, intended: str | None = None, action: str = "wrote") -> str:
    """Proof-of-write receipt: what is on disk, and whether it survives the session.

    The hash is taken from bytes read back off disk, never from the string we
    meant to write — an echo of intent is not evidence.
    """
    import hashlib

    if not p.exists():
        return json.dumps(
            {
                "ok": False,
                "action": action,
                "error": "file does not exist after write",
                "path": p.name,
                "abs_path": str(p),
            },
            indent=2,
        )

    raw = p.read_bytes()
    receipt = {
        "ok": True,
        "action": action,
        "path": p.resolve().relative_to(base.resolve()).as_posix()
        if str(p.resolve()).startswith(str(base.resolve()))
        else str(p),
        "abs_path": str(p),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "verified_on_disk": True,
    }
    if intended is not None:
        matches = raw == intended.encode("utf-8")
        receipt["verified_on_disk"] = matches
        if not matches:
            receipt["ok"] = False
            receipt["error"] = (
                "content on disk does not match what was written — do not report success"
            )
    receipt.update(_durability(p))
    return json.dumps(receipt, indent=2)


def _curl(url: str, method: str = "GET", body: dict | None = None, timeout: int = 120) -> str:
    cmd = ["curl", "-sf", "-X", method, url]
    if TOKEN and "127.0.0.1:8000" in url:
        cmd.extend(["-H", f"Authorization: Bearer {TOKEN}"])
    if body is not None:
        cmd.extend(["-H", "Content-Type: application/json", "-d", json.dumps(body)])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        return f"request failed: {proc.stderr or proc.stdout}"
    return proc.stdout


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


def _km_receipt(result, action: str) -> str:
    """Turn a KnowledgeManager return value into a durability receipt when it names a file."""
    raw = str(result)
    try:
        p = Path(raw)
        if p.is_absolute() and p.is_file():
            return _receipt(p, VAULT, action=action)
    except (OSError, ValueError):
        pass
    return json.dumps(
        {
            "ok": True,
            "action": action,
            "result": raw[:2000],
            "durability": "unknown",
            "warning": (
                "This tool did not return a file path, so durability could not be "
                "verified. Call vault_durability before describing the result as saved."
            ),
        },
        indent=2,
    )


@mcp.tool()
def ingest_to_ravenstack(source: str, content_or_path: str) -> str:
    """Ingest distilled content into Ravenstack backlog (ORACLE rules).

    Returns a durability receipt — see write_vault_file.
    """
    return _km_receipt(
        _km().ingest_document(source, content_or_path, auto_categorize=True), "ingested"
    )


@mcp.tool()
def save_ravenstack_note(source: str, distilled: str, potential_for: str = "revenue-loops") -> str:
    """Write a distilled note to Ravenstack backlog with frontmatter.

    Returns a durability receipt — see write_vault_file.
    """
    return _km_receipt(_km().save_to_backlog(source, distilled, potential_for), "saved")


# --- Vault read/write (real-time) ---


@mcp.tool()
def read_vault_file(relative_path: str, max_chars: int = 12000) -> str:
    """Read a file under the Obsidian vault (e.g. Rural Data/foo.md)."""
    p = _safe_path(VAULT, relative_path)
    if not p.exists():
        return f"not found: {relative_path}"
    return p.read_text(encoding="utf-8", errors="replace")[:max_chars]


@mcp.tool()
def write_vault_file(relative_path: str, content: str) -> str:
    """Write or update a file under the Obsidian vault. Creates parent dirs.

    Returns a JSON receipt: sha256 of the bytes actually on disk, plus whether
    the file is committed and pushed. A write succeeding does not make the work
    durable — read `durability` and `warning` before telling anyone it is saved.
    """
    p = _safe_path(VAULT, relative_path)
    existed = p.exists()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return _receipt(p, VAULT, intended=content, action="updated" if existed else "created")


@mcp.tool()
def vault_durability(relative_path: str = "") -> str:
    """Will this survive the session? Check one vault file, or sweep the whole vault.

    With a path: durability receipt for that file. Without: every uncommitted
    file in the vault. Call this before claiming work is saved or shared, and
    at session end before reporting anything as durable.
    """
    if relative_path:
        p = _safe_path(VAULT, relative_path)
        if not p.exists():
            return json.dumps(
                {"ok": False, "path": relative_path, "error": "not found"}, indent=2
            )
        return _receipt(p, VAULT, action="checked")

    rc, root = _git(VAULT, "rev-parse", "--show-toplevel")
    if rc != 0:
        return json.dumps({"git_repo": False, "vault": str(VAULT)}, indent=2)
    _, branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    _, porcelain = _git(root, "status", "--porcelain")
    files = [ln[3:] for ln in porcelain.splitlines() if ln.strip()]
    _, ahead = _git(root, "rev-list", "--count", "@{u}..HEAD")
    out = {
        "vault": str(root),
        "branch": branch,
        "uncommitted_files": len(files),
        "commits_ahead_of_remote": ahead if ahead.isdigit() else "unknown",
        "files": files[:100],
    }
    if files or (ahead.isdigit() and int(ahead) > 0):
        out["warning"] = (
            f"{len(files)} uncommitted file(s), {ahead} unpushed commit(s). This work "
            "exists on one machine. No session that clones the repo can see it. Commit "
            "and push before describing any of it as saved, shared, or cross-session memory."
        )
    return json.dumps(out, indent=2)


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


@mcp.tool()
def connector_help() -> str:
    """How this connector works — Grok Build, SuperGrok-style remote, Gemini."""
    return f"""ReClaw Platform MCP — unified connector

WHAT IT IS (like SuperGrok → GitHub):
  One MCP server exposing tools so the model can SEE and CHANGE your stack in real time.

GROK BUILD (this server — best experience):
  Config: ~/.grok/config.toml → [mcp_servers.reclaw-platform]
  Tools appear as: reclaw-platform__read_vault_file, reclaw-platform__run_pike_winslow, etc.
  Set XAI_API_KEY in /root/.env for xAI models.

REMOTE (Grok/Gemini from your PC):
  HTTP MCP on tailnet: https://openclaw.tail20a090.ts.net/reclaw-mcp/mcp
  Grok config:
    [mcp_servers.reclaw-platform]
    url = "https://openclaw.tail20a090.ts.net/reclaw-mcp/mcp"

STDIO over SSH:
  ssh root@178.156.235.36 '{ROOT}/.venv/bin/python {ROOT}/scripts/reclaw_platform_mcp_server.py'

WRITE TOOLS: write_vault_file, save_ravenstack_note, ingest_to_ravenstack, run_pike_winslow
READ TOOLS: read_vault_file, read_repo_file, query_knowledge, read_oracle
OPS: stack_health, docker_status, git_status, vault_durability

WRITE RECEIPTS (why writes return JSON, not "wrote N chars"):
  A successful write says nothing about whether the work survives the session.
  Every write tool returns sha256 of the bytes read back OFF DISK — not an echo
  of what was sent — plus committed / pushed / durability.

  durability: "pushed"               → safe to call saved and shared
              "committed-not-pushed" → survives restart, not a lost box
              "local-only"           → ONE MACHINE. No clone can see it.
              "unknown"              → not versioned; claim nothing

  The vault (/root/obsidian_vault) and the vault repo (github.com/jasandroidx/
  obsidian-vault) are two different things wearing one name. A write to the
  first is not durable until it reaches the second. Say which one you mean.

  Call vault_durability with no arguments before ending a session — it lists
  every uncommitted file. Do not report work as saved while that list is
  non-empty.

Also available separately: ravenstack, reclaw-api, reclaw-fs, obsidian MCPs.
"""


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport not in ("stdio", "sse", "streamable-http"):
        transport = "stdio"
    mcp.run(transport=transport)  # type: ignore[arg-type]
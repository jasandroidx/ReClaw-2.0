#!/usr/bin/env python3
"""
Zero-LLM morning fortress brief for Jason.

Cost: $0 (curl + docker only; no OpenRouter / no chat model).
Writes: outbox + Ravenstack ops + Raziel memory.
Optional: Discord ping if OPENCLAW_MORNING_DISCORD_TARGET is set or default allowlist id.

Schedule: systemd timer 08:00 America/Indiana/Indianapolis
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Indiana/Indianapolis")
OUTBOX = Path("/root/outbox")
VAULT_OPS = Path("/root/obsidian_vault/Ravenstack/ops")
MEMORY = Path("/root/.openclaw/workspace/memory")
# Discord user/channel from existing pairing allowlist (override via env)
DISCORD_TARGET = os.environ.get(
    "OPENCLAW_MORNING_DISCORD_TARGET", "user:1003239749147967528"
)


def _curl_json(url: str, timeout: int = 8) -> dict | list | str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "morning-fortress-brief/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw[:500]
    except Exception as exc:  # noqa: BLE001
        return {"_error": str(exc)}


def _sh(cmd: str, timeout: int = 20) -> str:
    try:
        p = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (p.stdout or "") + (p.stderr or "")
        return out.strip()[:2000]
    except Exception as exc:  # noqa: BLE001
        return f"error: {exc}"


def _disk() -> str:
    return _sh("df -h / | tail -1")


def _docker() -> str:
    return _sh("cd /root/ReClaw-2.0 && docker compose ps --format 'table {{.Name}}\t{{.Status}}' 2>/dev/null | head -10")


def _queue_snippet() -> str:
    # Prefer local status file if present
    for p in (
        Path("/root/ReClaw-2.0/data/county_queue.json"),
        Path("/root/ReClaw-2.0/data/county_queue/status.json"),
        Path("/root/ReClaw-2.0/dashboard/data/status.json"),
    ):
        if p.is_file():
            try:
                d = json.loads(p.read_text())
                cq = d.get("county_queue") or d
                return (
                    f"status={cq.get('status')} cursor={cq.get('cursor')}/"
                    f"{cq.get('total') or cq.get('total_counties')} "
                    f"pending={cq.get('pending_county') or cq.get('current')}"
                )
            except Exception:  # noqa: BLE001
                continue
    # dashboard status
    st = Path("/root/ReClaw-2.0/dashboard/status.json")
    if st.is_file():
        try:
            d = json.loads(st.read_text())
            cq = d.get("county_queue") or {}
            return (
                f"status={cq.get('status')} cursor={cq.get('cursor')}/"
                f"{cq.get('total')} pending={cq.get('pending_county')}"
            )
        except Exception:  # noqa: BLE001
            pass
    return "queue status file not found (check MCP sitrep later)"


def build_brief() -> str:
    now = datetime.now(TZ)
    utc = datetime.now(timezone.utc)
    day = now.date().isoformat()

    api = _curl_json("http://127.0.0.1:8000/health")
    oc = _curl_json("http://127.0.0.1:18789/health")
    mcp = _curl_json("http://127.0.0.1:8100/health")
    ollama = _curl_json("http://127.0.0.1:11434/api/tags")

    def ok(x) -> str:
        if isinstance(x, dict) and x.get("_error"):
            return f"DOWN ({x['_error'][:80]})"
        if isinstance(x, dict) and (x.get("ok") is True or x.get("status") in ("ok", "live", "healthy")):
            return "OK"
        if x is not None and not (isinstance(x, dict) and "_error" in x):
            return "OK"
        return "UNKNOWN"

    ollama_n = 0
    if isinstance(ollama, dict) and "models" in ollama:
        ollama_n = len(ollama.get("models") or [])

    grant = Path("/root/ReClaw-2.0/data/grant_digests")
    grants = sorted(grant.glob("*.md"), reverse=True)[:3] if grant.is_dir() else []
    grant_lines = "\n".join(f"- `{g.name}`" for g in grants) or "- (none yet)"

    lines = [
        f"# Morning fortress brief — {day}",
        "",
        f"_Generated **free** (no LLM) · local {now.strftime('%Y-%m-%d %H:%M %Z')} · UTC {utc.strftime('%H:%M')}_",
        f"_Cost: $0 · script: `scripts/morning_fortress_brief.py`_",
        "",
        "## Stack (live probes)",
        f"| Service | Status |",
        f"|---------|--------|",
        f"| ReClaw API :8000 | {ok(api)} |",
        f"| OpenClaw gateway :18789 | {ok(oc)} |",
        f"| MCP :8100 | {ok(mcp)} |",
        f"| Ollama | {ok(ollama)} · models={ollama_n} |",
        "",
        "## Docker",
        "```",
        _docker() or "(no output)",
        "```",
        "",
        "## County queue",
        f"- {_queue_snippet()}",
        "- **FROZEN policy:** do not run-next unless Jason unfreezes",
        "",
        "## Disk",
        f"- `{_disk()}`",
        "",
        "## Grant digests (latest)",
        grant_lines,
        "",
        "## Top 3 (suggested — not auto-done)",
        "1. Open latest grant digest; pick 1–3 for a human pilot if ready",
        "2. If anything above is DOWN — fix that first (mechanic/sitrep)",
        "3. One fortress win today (USER.md, morning brief, or grant polish)",
        "",
        "## Free daily lanes (reminders)",
        "- **Ops heartbeat** already uses `ollama/phi4-mini` (local $0)",
        "- **OpenRouter free** aliases: `or-oss`, `or-gemma`, `or-nemotron` when local busy",
        "- **Research agent** can use free/cloud free tiers for digests (watch rate limits)",
        "",
        "## Outbox",
        f"- http://100.108.130.82:8765/morning-brief-{day}.md",
        "",
        "status: ok",
        "",
    ]
    return "\n".join(lines)


def write_outputs(text: str) -> list[Path]:
    day = datetime.now(TZ).date().isoformat()
    paths = []
    OUTBOX.mkdir(parents=True, exist_ok=True)
    VAULT_OPS.mkdir(parents=True, exist_ok=True)
    MEMORY.mkdir(parents=True, exist_ok=True)

    for p in (
        OUTBOX / f"morning-brief-{day}.md",
        OUTBOX / "morning-brief-latest.md",
        VAULT_OPS / f"morning-brief-{day}.md",
        MEMORY / f"{day}-morning.md",
    ):
        p.write_text(text)
        paths.append(p)
    return paths


def try_discord(text: str) -> str:
    """Best-effort Discord ping via openclaw CLI (gateway container)."""
    # Keep Discord short — full brief is in outbox
    day = datetime.now(TZ).date().isoformat()
    summary = (
        f"**Morning fortress brief** ({day}) — $0 / no LLM\n"
        f"Full: http://100.108.130.82:8765/morning-brief-{day}.md\n"
        f"(Also vault ops + Raziel memory)\n"
    )
    # Extract stack table lines roughly
    for line in text.splitlines():
        if "ReClaw API" in line or "OpenClaw gateway" in line or "MCP" in line or "Ollama" in line:
            summary += line.replace("|", " ").strip() + "\n"
    summary = summary[:1800]
    target = DISCORD_TARGET
    cmd = [
        "docker",
        "exec",
        "openclaw-gateway",
        "openclaw",
        "message",
        "send",
        "--channel",
        "discord",
        "--target",
        target,
        "--message",
        summary,
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        out = ((p.stdout or "") + (p.stderr or "")).strip()
        if p.returncode == 0:
            return f"discord_ok target={target} {out[:200]}"
        return f"discord_fail rc={p.returncode} {out[:400]}"
    except Exception as exc:  # noqa: BLE001
        return f"discord_error {exc}"


def main() -> int:
    text = build_brief()
    paths = write_outputs(text)
    disc = try_discord(text)
    print("WROTE:")
    for p in paths:
        print(" ", p)
    print("DISCORD:", disc)
    print("---")
    print(text[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

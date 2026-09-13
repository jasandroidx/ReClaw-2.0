#!/usr/bin/env python3
"""Write a session digest into the Ravenstack vault when a session ends.

Wired as a Stop hook in .claude/settings.json. Replaces having to remember to
type "end session" — the whole point is that it fires whether or not the
operator remembers, including at 2am.

Reads the hook payload on stdin (session_id, transcript_path, cwd), walks the
transcript, and writes:

    $RECLAW_OBSIDIAN_VAULT_PATH/Ravenstack/ops/sessions/YYYY-MM-DD-HHMM-<id>.md

Design rules:
  - Never fail. A hook that raises on session exit is worse than no hook, so
    everything is wrapped and the script always exits 0.
  - Facts first. The deterministic half (files touched, commits, commands) is
    written even when the model half is unavailable.
  - The narrative is best-effort via local Ollama with a short timeout. If
    Ollama is down the note still lands, just without prose.

Frontmatter follows Ravenstack/RAVENSTACK-ORACLE.md conventions; if those
change, change them here too.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

VAULT = Path(os.environ.get("RECLAW_OBSIDIAN_VAULT_PATH", "/root/obsidian_vault"))
OUT_DIR = VAULT / "Ravenstack" / "ops" / "sessions"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.environ.get("RAVENSTACK_DIGEST_MODEL", "gemma4")
OLLAMA_TIMEOUT = float(os.environ.get("RAVENSTACK_DIGEST_TIMEOUT", "45"))

# Transcripts can be very large; cap what we walk and what we send to a model.
MAX_LINES = 6000
MAX_PROMPT_CHARS = 12000


def _blocks(msg):
    """Content blocks for a transcript message, whatever shape it arrived in."""
    content = msg.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    return []


def read_transcript(path: Path):
    """Pull the few things worth remembering out of a session transcript."""
    prompts: list[str] = []
    files: set[str] = set()
    commands: list[str] = []

    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if i > MAX_LINES:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg = ev.get("message") or {}
                if not isinstance(msg, dict):
                    continue
                role = msg.get("role") or ev.get("role")

                for b in _blocks(msg):
                    kind = b.get("type")
                    if kind == "text" and role == "user":
                        text = (b.get("text") or "").strip()
                        # Skip harness noise; keep what the human actually said.
                        if text and not text.startswith((
                            "<system-reminder", "Caveat:", "<local-command",
                            "<command-name", "[Request interrupted",
                        )):
                            prompts.append(text)
                    elif kind == "tool_use":
                        name = b.get("name") or ""
                        inp = b.get("input") or {}
                        if not isinstance(inp, dict):
                            continue
                        if name in ("Edit", "Write", "NotebookEdit"):
                            fp = inp.get("file_path")
                            if fp:
                                files.add(str(fp))
                        elif name == "Bash":
                            cmd = (inp.get("command") or "").strip()
                            if cmd:
                                commands.append(cmd)
    except Exception:
        pass

    return prompts, sorted(files), commands


def git_commits(cwd: str) -> list[str]:
    """Commits landed in the last day — the durable record of the session."""
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "log", "--since=1.day", "--oneline", "--no-merges"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            return [l for l in out.stdout.splitlines() if l.strip()][:25]
    except Exception:
        pass
    return []


def narrative(prompts, files, commits) -> str:
    """Best-effort prose from the local model. Silence beats a stall."""
    if not prompts:
        return ""
    body = "\n".join(f"- {p[:400]}" for p in prompts[:25])
    changed = "\n".join(f"- {f}" for f in files[:30]) or "- (none)"
    landed = "\n".join(f"- {c}" for c in commits) or "- (none)"
    prompt = (
        "Summarise this development session for a project log. Be concrete and "
        "brief. No praise, no filler.\n\n"
        "## What the operator asked for\n" + body + "\n\n"
        "## Files changed\n" + changed + "\n\n"
        "## Commits\n" + landed + "\n\n"
        "Write exactly three sections:\n"
        "### What happened\n(3-5 bullets)\n"
        "### Unfinished\n(anything left open, or 'nothing')\n"
        "### Worth remembering next time\n"
        "(lessons, gotchas, wrong turns — the things that would save the next "
        "session time. If none, say so.)\n"
    )[:MAX_PROMPT_CHARS]

    try:
        import urllib.request

        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
            return (json.loads(resp.read().decode("utf-8", "replace")).get("response") or "").strip()
    except Exception:
        return ""


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}

    session_id = str(payload.get("session_id") or "unknown")
    cwd = str(payload.get("cwd") or os.getcwd())
    tpath = payload.get("transcript_path")

    prompts, files, commands = ([], [], [])
    if tpath:
        p = Path(str(tpath))
        if p.is_file():
            prompts, files, commands = read_transcript(p)

    commits = git_commits(cwd)

    # A session that changed nothing and said nothing is not worth a note.
    if not prompts and not files and not commits:
        return 0

    now = datetime.now(timezone.utc)
    short = re.sub(r"[^a-zA-Z0-9]", "", session_id)[:8] or "session"
    out = OUT_DIR / f"{now:%Y-%m-%d-%H%M}-{short}.md"

    topic = (prompts[0].splitlines()[0][:90] if prompts else "session").replace('"', "'")
    notable = [c for c in commands if re.search(r"\bgit (commit|push|merge|rebase)\b", c)][:10]

    lines = [
        "---",
        f'date: {now:%Y-%m-%d}',
        f'time_utc: "{now:%H:%M}"',
        "source: claude-code-session-digest",
        f'session_id: "{session_id}"',
        f'cwd: "{cwd}"',
        f'topic: "{topic}"',
        "tags: [ravenstack, ops, session]",
        "---",
        "",
        f"# Session — {now:%Y-%m-%d %H:%M} UTC",
        "",
    ]

    prose = narrative(prompts, files, commits)
    if prose:
        lines += [prose, ""]
    else:
        lines += [
            "> Narrative unavailable (local model unreachable). Facts below are complete.",
            "",
        ]

    if prompts:
        lines += ["## Asked for", ""]
        lines += [f"- {p.splitlines()[0][:200]}" for p in prompts[:15]]
        lines += [""]

    if commits:
        lines += ["## Commits", "", "```"] + commits + ["```", ""]

    if files:
        lines += ["## Files changed", ""] + [f"- `{f}`" for f in files[:40]] + [""]

    if notable:
        lines += ["## Git operations", "", "```"] + notable + ["```", ""]

    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(json.dumps({"systemMessage": f"Session digest → {out}"}))
    except Exception as exc:
        print(json.dumps({"systemMessage": f"Session digest failed: {exc}"}))

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Never let a digest failure surface as a session-exit error.
        sys.exit(0)

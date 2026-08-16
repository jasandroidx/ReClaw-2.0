"""The Oracle — deterministic routing and refusal for vault writes.

She exists because a model lied once and it hurt. So she is not a model. She
does not infer, summarise, or guess: she reads Ravenstack/oracle-routes.yaml
and answers from it, or says she has no rule. A wrong answer delivered
confidently is the failure mode she was created to prevent, so "I don't know"
is a first-class result here, not an error path.

Two entry points:

    ask(question)               -> where does this go, what frontmatter
    check(path, frontmatter)    -> permit or refuse, with a reason

`check` is the one that matters. It is called *inside* the vault writers, so a
client that has never read a word of Ravenstack still cannot write to the wrong
place with the wrong frontmatter. Rules that live in prose are advice; rules
that live here are enforcement.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

VAULT = Path(os.environ.get("RECLAW_OBSIDIAN_VAULT_PATH", "/root/obsidian_vault"))
ROUTES_FILE = VAULT / "Ravenstack" / "oracle-routes.yaml"

_cache: dict[str, Any] = {}
_cache_mtime: float | None = None


class OracleUnavailable(RuntimeError):
    """The routes file is missing or unparseable."""


def routes() -> dict[str, Any]:
    """Load the law, re-reading it when the file changes on disk."""
    global _cache, _cache_mtime
    try:
        mtime = ROUTES_FILE.stat().st_mtime
    except OSError as exc:
        raise OracleUnavailable(f"No routes at {ROUTES_FILE}: {exc}") from exc

    if _cache and _cache_mtime == mtime:
        return _cache

    try:
        data = yaml.safe_load(ROUTES_FILE.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise OracleUnavailable(f"Routes file is not valid YAML: {exc}") from exc

    if not isinstance(data, dict) or "routes" not in data:
        raise OracleUnavailable("Routes file has no `routes` section")

    _cache, _cache_mtime = data, mtime
    return data


def _voice(key: str, **fmt: Any) -> str:
    line = (routes().get("voice") or {}).get(key, "")
    try:
        return line.format(**fmt).strip()
    except (KeyError, IndexError):
        return line.strip()


@dataclass
class Verdict:
    """A ruling. `ok` is the only thing callers should branch on."""

    ok: bool
    message: str
    kind: str | None = None
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return self.message


# ── ask ─────────────────────────────────────────────────────────────────────

# Keywords are matched against the question. Deliberately literal: a lookup
# table cannot hallucinate a destination, and a near-miss returning "no rule"
# is the correct outcome.
_HINTS: dict[str, tuple[str, ...]] = {
    "distillation": ("pdf", "book", "article", "distil", "distill", "ingest", "paper", "web page"),
    "session": ("session", "digest", "end of session", "transcript"),
    "ops": ("ops", "audit", "incident", "run log", "operational", "sitrep"),
    "agent": ("agent", "soul", "persona", "spec"),
    "architecture": ("architecture", "design", "component", "how it works"),
    "protocol": ("protocol", "procedure", "ritual", "checklist", "workflow"),
    "claim": ("claim", "assertion", "evidence", "sourced"),
    "research": ("research", "investigation", "comparison", "finding"),
    "library": ("library", "reading", "chapter"),
    "skill": ("skill",),
    "keep": ("keep", "room art", "seat", "sprite"),
    "county": ("county", "indiana", "rural", "pike", "gateway", "package"),
    "room": ("room", "chamber", "wing"),
    "inbox": ("inbox", "unprocessed", "staging"),
    "knowledge": ("note", "topic", "knowledge", "remember", "save"),
}


def ask(question: str) -> str:
    """Answer 'where does this go?' from the table, or refuse to guess."""
    try:
        data = routes()
    except OracleUnavailable as exc:
        return f"The Oracle cannot see. {exc}"

    q = (question or "").lower().strip()
    if not q:
        return _voice("no_rule")

    # Longest keyword wins, so "session digest" beats a bare "session".
    best_kind, best_len = None, 0
    for kind, words in _HINTS.items():
        if kind not in data["routes"]:
            continue
        for w in words:
            if w in q and len(w) > best_len:
                best_kind, best_len = kind, len(w)

    if not best_kind:
        return _voice("no_rule")

    r = data["routes"][best_kind]
    fm = dict(data.get("frontmatter", {}).get("required", []) and
              {k: "<required>" for k in data["frontmatter"]["required"]})
    fm.update(r.get("frontmatter") or {})
    for extra in r.get("extra_required") or []:
        fm[extra] = "<required>"

    lines = [
        f"**{best_kind}** — {(r.get('what') or '').strip()}",
        "",
        f"- path: `{r.get('path')}/{r.get('filename', '')}`",
        f"- frontmatter: {', '.join(f'{k}: {v}' for k, v in fm.items())}",
        f"- write with: `{r.get('tool', 'write_vault_file')}`",
    ]
    if r.get("note"):
        lines += ["", str(r["note"]).strip()]
    return "\n".join(lines)


# ── check ───────────────────────────────────────────────────────────────────

_SECRET_PATTERNS = (
    re.compile(r"\b(AIza[0-9A-Za-z_\-]{30,}|sk-[A-Za-z0-9]{20,}|xai-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,})"),
)


def _kind_for_path(data: dict[str, Any], rel: str) -> str | None:
    """Deepest matching route wins, so ops/sessions beats ops."""
    best, best_len = None, -1
    for kind, r in data["routes"].items():
        p = str(r.get("path") or "").strip("/")
        if p and (rel == p or rel.startswith(p + "/")) and len(p) > best_len:
            best, best_len = kind, len(p)
    return best


def check(
    path: str | Path,
    frontmatter: dict[str, Any] | None = None,
    content: str | None = None,
) -> Verdict:
    """Permit or refuse a proposed vault write."""
    try:
        data = routes()
    except OracleUnavailable as exc:
        # Fail OPEN: a missing rulebook must not brick every write. Loud, though.
        return Verdict(True, f"The Oracle is blind ({exc}) — write permitted unchecked.",
                       warnings=["oracle-routes.yaml unreadable"])

    raw = str(path)

    for bad in data.get("forbidden_paths") or []:
        if str(bad.get("path", "")) and str(bad["path"]) in raw:
            return Verdict(False, _voice("refused_path", reason=str(bad.get("reason", "")).strip()))

    if content:
        for pat in _SECRET_PATTERNS:
            if pat.search(content):
                return Verdict(False, _voice(
                    "refused_secret",
                    reason="That looks like a live API key. Secrets belong in .env, never the vault.",
                ))
        funnel = os.environ.get("MCP_FUNNEL_PATH", "").strip("/")
        if funnel and funnel in content:
            return Verdict(False, _voice(
                "refused_secret",
                reason="That contains the Funnel path, which is an unauthenticated secret.",
            ))

    # Normalise to a vault-relative path.
    rel = raw
    for prefix in (str(VAULT), "/root/obsidian_vault"):
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
            break
    rel = rel.strip("/")

    kind = _kind_for_path(data, rel)
    if kind is None:
        return Verdict(False, _voice("no_rule"))

    fm = {k.lower(): v for k, v in (frontmatter or {}).items()}
    required = list(data.get("frontmatter", {}).get("required") or [])
    required += list(data["routes"][kind].get("extra_required") or [])

    missing = [k for k in required if not fm.get(k)]
    if missing:
        return Verdict(False, _voice("refused_frontmatter", missing=", ".join(missing)),
                       kind=kind, missing=missing)

    warnings: list[str] = []
    known_types = data.get("frontmatter", {}).get("known_types") or []
    if fm.get("type") and known_types and fm["type"] not in known_types:
        warnings.append(f"unrecognised type '{fm['type']}' (not blocking)")
    for rec in data.get("frontmatter", {}).get("recommended") or []:
        if not fm.get(rec):
            warnings.append(f"missing recommended '{rec}'")

    return Verdict(True, _voice("ok", path=rel), kind=kind, warnings=warnings)

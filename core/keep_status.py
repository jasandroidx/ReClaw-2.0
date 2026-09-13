"""GET /keep/status — read-only pulse for the Keep door + hall strip.

Prefers status.json. Does not talk to MCP :8100. Does not use the Docker socket.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException

router = APIRouter()

STALE_AFTER_SEC = 60 * 60
STATUS_CANDIDATES = (
    Path("/data/dashboard/status.json"),
    Path("/app/dashboard/status.json"),
    Path("/root/ReClaw-2.0/dashboard/status.json"),
    Path("dashboard/status.json"),
    Path("/data/status.json"),
)
OK = {"ok", "up", "live", "healthy"}
SKIP = {"unprobed", "unknown", "skipped", "omitted", ""}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_status() -> tuple[dict[str, Any] | None, str | None]:
    for path in STATUS_CANDIDATES:
        try:
            if path.is_file():
                return json.loads(path.read_text(encoding="utf-8")), str(path)
        except (OSError, ValueError):
            continue
    return None, None


def _svc_flag(raw: Any) -> str:
    if not raw or not isinstance(raw, dict):
        return "unknown"
    st = str(raw.get("status", "")).lower()
    if st in SKIP:
        return "unprobed"
    if raw.get("ok") is True or st in OK:
        return "up"
    if raw.get("ok") is False or st in {"down", "dead", "error"}:
        return "down"
    return "unknown"


def _pulse(doc: dict[str, Any] | None) -> tuple[str, str]:
    if not doc:
        return "PAPER", "no status.json"
    generated = _parse_ts(doc.get("generated_at"))
    if generated is None:
        return "PAPER", "status.json has no generated_at"
    age = (_now() - generated).total_seconds()
    services = doc.get("services") or {}
    down = []
    for key, name in (("reclaw_api", "reclaw_api"), ("openclaw", "openclaw"), ("mcp", "mcp")):
        flag = _svc_flag(services.get(key))
        if flag == "down":
            down.append(name)
    if down:
        return "BREACH", ",".join(down)
    if age > STALE_AFTER_SEC:
        return "STALE", f"generated_at age_sec={int(age)}"
    return "LIVE", f"generated_at age_sec={int(age)}"


def _containers(doc: dict[str, Any] | None) -> list[dict[str, str]]:
    if not doc:
        return []
    services = doc.get("services") or {}
    pairs = (
        ("reclaw-api", services.get("reclaw_api")),
        ("openclaw-gateway", services.get("openclaw")),
        ("reclaw-platform-mcp", services.get("mcp")),
    )
    return [{"name": n, "state": _svc_flag(raw)} for n, raw in pairs]


@router.get("/keep/status")
def keep_status(x_keep_token: str | None = Header(default=None, alias="X-Keep-Token")):
    expected = (os.environ.get("KEEP_TOKEN") or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="KEEP_TOKEN unset")
    if not x_keep_token or x_keep_token.strip() != expected:
        raise HTTPException(status_code=401, detail="unauthorized")

    doc, path = _load_status()
    pulse, reason = _pulse(doc)
    services = (doc or {}).get("services") or {}
    occ = (doc or {}).get("occupancy")
    if not occ:
        occ = "fixture" if pulse in ("PAPER", "STALE") else "unknown"
    return {
        "pulse": pulse,
        "reason": reason,
        "read_at": _now().isoformat().replace("+00:00", "Z"),
        "source": path,
        "generated_at": (doc or {}).get("generated_at"),
        "containers": _containers(doc),
        "openclaw": services.get("openclaw"),
        "mcp": services.get("mcp"),
        "ollama_models": services.get("ollama_models"),
        "rooms": (doc or {}).get("rooms") or [],
        "agents_active": (doc or {}).get("agents_active"),
        "tunnel": (doc or {}).get("tunnel"),
        "occupancy": occ,
    }

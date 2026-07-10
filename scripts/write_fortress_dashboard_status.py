#!/usr/bin/env python3
"""Write dashboard/status.json from live probes so the static fortress UI shows live data."""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dashboard" / "status.json"
GATEWAY = os.environ.get("RECLAW_GATEWAY_URL", "http://127.0.0.1:8000")
OPENCLAW = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")
MAP = ROOT / "dashboard" / "data" / "castle_map.json"


def _get_json(url: str, timeout: float = 5.0) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception as e:
        return f"error: {e}"


def main() -> int:
    reclaw = _get_json(f"{GATEWAY}/health")
    openclaw = _get_json(f"{OPENCLAW}/health")
    queue = _get_json(f"{GATEWAY}/county-queue/status")
    mcp = _get_json("http://127.0.0.1:8100/health")
    ollama = _get_json("http://127.0.0.1:11434/api/tags")

    rooms = []
    agents_active = 0
    if MAP.is_file():
        try:
            cmap = json.loads(MAP.read_text(encoding="utf-8"))
            for r in cmap.get("rooms") or []:
                empty = bool(r.get("empty"))
                if not empty:
                    agents_active += 1
                rooms.append(
                    {
                        "id": r.get("id"),
                        "name": r.get("name"),
                        "empty": empty,
                        "agent": (r.get("agent") or {}).get("name"),
                        "status": (r.get("agent") or {}).get("status") if not empty else "UNFORGED",
                    }
                )
        except (json.JSONDecodeError, OSError):
            pass

    reclaw_ok = isinstance(reclaw, dict) and reclaw.get("status") in ("ok", "healthy")
    oc_ok = isinstance(openclaw, dict) and (
        openclaw.get("ok") is True or openclaw.get("status") in ("live", "ok", "healthy")
    )
    mcp_ok = isinstance(mcp, dict) and mcp.get("status") == "ok"

    if reclaw_ok and oc_ok and mcp_ok:
        network = "CONNECTED"
        network_detail = "RECLAW + OPENCLAW + MCP OK"
    elif reclaw_ok and oc_ok:
        network = "PARTIAL"
        network_detail = "RECLAW + OPENCLAW OK / MCP ?"
    elif reclaw_ok:
        network = "DEGRADED"
        network_detail = "RECLAW OK / OPENCLAW or MCP down"
    else:
        network = "DISCONNECTED"
        network_detail = "API unreachable from poller"

    public_url = ""
    uf = ROOT / "data" / "mcp_public_url.txt"
    if uf.is_file():
        public_url = uf.read_text(encoding="utf-8", errors="replace").strip()

    status = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "network": network,
        "network_detail": network_detail,
        "data_source": "LIVE status.json",
        "agents_active": agents_active,
        "rooms": rooms,
        "services": {
            "reclaw_api": reclaw or {"status": "down"},
            "openclaw": openclaw or {"status": "down"},
            "mcp": mcp or {"status": "down"},
            "ollama_models": len((ollama or {}).get("models") or []) if ollama else 0,
        },
        "county_queue": {
            "status": (queue or {}).get("queue_status"),
            "cursor": (queue or {}).get("cursor"),
            "total": (queue or {}).get("total_counties"),
            "pending_county": ((queue or {}).get("pending_review") or {}).get("county"),
            "pending_flags": ((queue or {}).get("pending_review") or {}).get("flag_count"),
            "top_finding": ((queue or {}).get("pending_review") or {}).get("top_finding"),
        }
        if queue
        else None,
        "mcp_public_url_present": bool(public_url),
        "bridge": _run(["systemctl", "is-active", "reclaw-mcp-bridge"]),
        "tunnel": _run(["systemctl", "is-active", "reclaw-mcp-tunnel"]),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} network={network}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

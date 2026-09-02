#!/usr/bin/env python3
"""
Zero-LLM fortress alert watch — speak only when something is wrong.

Checks:
  1. Linux PC OpenClaw node connected (expected display name)
  2. Root disk usage (warn >= 85%, critical >= 90%)
  3. Optional: month cost total from vault cost-log / cost summary if present

Discord: only if any alert fires (or FORCE=1).
State: /var/lib/reclaw/fortress-alert-state.json (dedupe repeat spam).

Schedule: systemd timer (default every 30m).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(os.environ.get("FORTRESS_ALERT_STATE", "/var/lib/reclaw/fortress-alert-state.json"))
DISCORD_TARGET = os.environ.get(
    "OPENCLAW_MORNING_DISCORD_TARGET",
    os.environ.get("FORTRESS_ALERT_DISCORD_TARGET", "user:1003239749147967528"),
)
EXPECTED_NODE = os.environ.get("FORTRESS_EXPECTED_NODE", "Linux PC (boydscomp)")
DISK_WARN = int(os.environ.get("FORTRESS_DISK_WARN_PCT", "85"))
DISK_CRIT = int(os.environ.get("FORTRESS_DISK_CRIT_PCT", "90"))
FORCE = os.environ.get("FORTRESS_ALERT_FORCE", "").strip() in ("1", "true", "yes")
COOLDOWN_SEC = int(os.environ.get("FORTRESS_ALERT_COOLDOWN_SEC", str(6 * 3600)))  # 6h per alert key
OUTBOX = Path("/root/outbox")
VAULT_COST_DIR = Path("/root/obsidian_vault/Ravenstack/ops/cost")
COST_LOG = Path("/root/obsidian_vault/Ravenstack/ops/harvest/cost-log.jsonl")


def _sh(cmd: str, timeout: int = 45) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = ((p.stdout or "") + (p.stderr or "")).strip()
        return p.returncode, out[:8000]
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def check_linux_node() -> list[str]:
    alerts: list[str] = []
    # Prefer JSON if available
    rc, out = _sh(
        "docker exec openclaw-gateway openclaw nodes status --json 2>/dev/null"
    )
    connected = False
    found = False
    if rc == 0 and out.strip().startswith(("{", "[")):
        try:
            data = json.loads(out)
            nodes = data if isinstance(data, list) else (
                data.get("nodes") or data.get("paired") or data.get("known") or []
            )
            if isinstance(data, dict) and not nodes:
                # try nested
                for k, v in data.items():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        nodes = v
                        break
            for n in nodes if isinstance(nodes, list) else []:
                if not isinstance(n, dict):
                    continue
                name = (
                    n.get("displayName")
                    or n.get("name")
                    or n.get("label")
                    or ""
                )
                nid = str(n.get("nodeId") or n.get("id") or "")
                status = str(n.get("status") or n.get("connection") or "").lower()
                connected_flag = n.get("connected")
                if EXPECTED_NODE.lower() in name.lower() or "boydscomp" in name.lower():
                    found = True
                    if connected_flag is True or "connected" in status:
                        connected = True
                    break
                # also match by partial
                if "boyds" in name.lower() or "linux pc" in name.lower():
                    found = True
                    if connected_flag is True or "connected" in status:
                        connected = True
        except json.JSONDecodeError:
            pass

    if not found:
        # text fallback
        rc2, text = _sh(
            "docker exec openclaw-gateway openclaw nodes status 2>/dev/null"
        )
        if "boydscomp" in text.lower() or "linux pc" in text.lower():
            found = True
            # connected line often: "paired · connected"
            for line in text.splitlines():
                low = line.lower()
                if "boyds" in low or "linux pc" in low or "linu" in low:
                    if "connected" in low and "disconnected" not in low:
                        connected = True
            # also global: Connected: 1 with Linux present
            if re.search(r"connected\s*\(", text, re.I) and "boyds" in text.lower():
                connected = True
            if "paired · connected" in text.lower() or "paired · connected" in text:
                # if Linux appears in table near connected
                if re.search(r"boydscomp|Linux PC", text, re.I):
                    # crude: status column contains connected for that node
                    if re.search(
                        r"(boydscomp|Linux PC).{0,200}connected",
                        text,
                        re.I | re.S,
                    ) or re.search(
                        r"connected.{0,80}(boyds|Linux)",
                        text,
                        re.I | re.S,
                    ):
                        connected = True
            # better crude parse: line with boydscomp and connected
            blob = text.replace("\n", " ")
            if re.search(r"Linux\s*PC.*?connected|boydscomp.*?connected", blob, re.I):
                connected = True
            # nodes status uses "Connected: N" and Linux row
            m = re.search(r"Connected:\s*(\d+)", text)
            if m and int(m.group(1)) >= 1 and found:
                # if only phone is disconnected and linux is the other...
                if "disconnected" in text.lower() and "boydscomp" in text.lower():
                    # check phone is the disconnected one
                    if re.search(
                        r"boydscomp[^\n]*connected|Linux PC[^\n]*connected|connected[^\n]*boyds",
                        text,
                        re.I,
                    ):
                        connected = True
                    elif "Phone" in text and "disconnected" in text:
                        # Linux might still be connected
                        connected = "connected" in text.lower() and "boydscomp" in text.lower()

    if not found:
        alerts.append(
            f"Linux node **{EXPECTED_NODE}** not in paired nodes list "
            f"(node host offline or unpaired)."
        )
    elif not connected:
        alerts.append(
            f"Linux node **{EXPECTED_NODE}** is paired but **not connected** "
            f"(start `openclaw node` on BoydsComp)."
        )
    return alerts


def check_disk() -> list[str]:
    alerts: list[str] = []
    rc, out = _sh("df -P / | tail -1")
    if rc != 0 or not out:
        alerts.append(f"Disk probe failed: {out[:120]}")
        return alerts
    # Filesystem 1024-blocks Used Available Capacity Mounted
    parts = out.split()
    if len(parts) >= 5:
        cap = parts[4].rstrip("%")
        try:
            pct = int(cap)
        except ValueError:
            pct = -1
        if pct >= DISK_CRIT:
            alerts.append(f"Disk **CRITICAL** {pct}% used on `/` (threshold {DISK_CRIT}%).")
        elif pct >= DISK_WARN:
            alerts.append(f"Disk **WARN** {pct}% used on `/` (threshold {DISK_WARN}%).")
    return alerts


def check_cost() -> list[str]:
    """Soft cost signals only — never invent spend."""
    alerts: list[str] = []
    # Prefer today's cost summary frontmatter if present
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    summary = VAULT_COST_DIR / f"{today}-cost-summary.md"
    if summary.is_file():
        text = summary.read_text(errors="replace")[:2000]
        m = re.search(r"month_total_usd:\s*([0-9.]+)", text)
        if m:
            try:
                total = float(m.group(1))
                cap = float(os.environ.get("COST_MONTHLY_USD_CAP", "25"))
                if total >= cap:
                    alerts.append(
                        f"Cost **month total ${total:.2f}** >= soft cap ${cap:.0f} "
                        f"(see `{summary}`)."
                    )
            except ValueError:
                pass
    return alerts


def check_gateway() -> list[str]:
    alerts: list[str] = []
    rc, out = _sh("curl -sf --max-time 5 http://127.0.0.1:18789/health")
    if rc != 0 or "live" not in out and '"ok":true' not in out.replace(" ", ""):
        # also accept {"ok":true
        if '"ok":true' not in out.replace(" ", "") and "'ok': true" not in out:
            alerts.append(f"OpenClaw gateway health **bad**: {out[:120] or 'no response'}")
    return alerts


def load_state() -> dict:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:  # noqa: BLE001
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


def filter_cooldown(alerts: list[str], state: dict) -> list[str]:
    now = time.time()
    last = state.get("last_sent") or {}
    out = []
    for a in alerts:
        key = re.sub(r"\s+", " ", a)[:120]
        prev = float(last.get(key) or 0)
        if FORCE or (now - prev) >= COOLDOWN_SEC:
            out.append(a)
    return out


def mark_sent(alerts: list[str], state: dict) -> dict:
    now = time.time()
    last = state.setdefault("last_sent", {})
    for a in alerts:
        key = re.sub(r"\s+", " ", a)[:120]
        last[key] = now
    state["last_run_utc"] = datetime.now(timezone.utc).isoformat()
    state["last_alert_count"] = len(alerts)
    return state


def send_discord(message: str) -> str:
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
        DISCORD_TARGET,
        "--message",
        message[:1800],
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        out = ((p.stdout or "") + (p.stderr or "")).strip()
        if p.returncode == 0:
            return f"discord_ok {out[:200]}"
        return f"discord_fail rc={p.returncode} {out[:400]}"
    except Exception as exc:  # noqa: BLE001
        return f"discord_error {exc}"


def write_quiet_log(alerts: list[str], sent: list[str], disc: str) -> Path:
    OUTBOX.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p = OUTBOX / f"fortress-alert-watch-{day}.log"
    line = (
        f"{datetime.now(timezone.utc).isoformat()} "
        f"alerts={len(alerts)} sent={len(sent)} {disc}\n"
    )
    if alerts:
        line += "  " + " | ".join(alerts) + "\n"
    with p.open("a") as f:
        f.write(line)
    return p


def main() -> int:
    alerts: list[str] = []
    alerts.extend(check_gateway())
    alerts.extend(check_linux_node())
    alerts.extend(check_disk())
    alerts.extend(check_cost())

    state = load_state()
    to_send = filter_cooldown(alerts, state)

    disc = "silent"
    if to_send:
        body = (
            "**Fortress alert** (zero-LLM watch)\n"
            + "\n".join(f"• {a}" for a in to_send)
            + "\n_Quiet otherwise. Cooldown ~6h per alert key._"
        )
        disc = send_discord(body)
        state = mark_sent(to_send, state)
    else:
        state["last_run_utc"] = datetime.now(timezone.utc).isoformat()
        state["last_alert_count"] = 0
        if alerts and not to_send:
            disc = "suppressed_cooldown"
        else:
            disc = "ok_silent"

    save_state(state)
    logp = write_quiet_log(alerts, to_send, disc)
    print(
        json.dumps(
            {
                "alerts": alerts,
                "sent": to_send,
                "discord": disc,
                "log": str(logp),
                "expected_node": EXPECTED_NODE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
# Watchdog for reclaw-platform-mcp.service (single-worker streamable-http on :8100).
#
# A slow tool call (e.g. `sitrep` / `project_sitrep`, which runs ~15 sequential
# checks including `openclaw doctor --lint`) can block every route, including
# /health, for 30-90+ seconds. A naive "restart after N failed /health probes"
# watchdog can't tell that apart from a genuinely dead process and kills a
# busy-but-alive bridge mid-request (root-caused 2026-08-17, recurred 2026-09-03
# during a 6-tool parallel burst -- restart fired at 20:19:05 mid-session).
#
# This version decides from kernel state first, in order:
#   1. systemd unit not active  -> stand down; Restart=always already owns this.
#   2. no listening socket      -> genuinely dead, restart now.
#   3. /health answers 200      -> healthy, reset counters.
#   4. /health slow/failed:
#        established connections on :8100 present -> BUSY, tolerate up to
#          BUSY_THRESHOLD consecutive probes (a real client is mid-request).
#        no established connections               -> probable hang, restart
#          after HANG_THRESHOLD consecutive probes (nobody's even connected,
#          so it can't be "busy serving someone").
set -uo pipefail

UNIT="reclaw-platform-mcp"
STATE_FILE="/root/ReClaw-2.0/data/mcp_bridge_watchdog_fail_count"
BUSY_THRESHOLD=45   # ~45 consecutive busy-but-connected minutes tolerated
HANG_THRESHOLD=10   # ~10 consecutive no-connection failures -> treat as hung

log() {
  logger -t mcp-watchdog "$1"
}

reset_and_exit() {
  echo 0 > "$STATE_FILE"
  exit 0
}

unit_state=$(systemctl is-active "$UNIT" 2>/dev/null || true)
if [[ "$unit_state" != "active" ]]; then
  log "unit state=$unit_state; standing down (systemd Restart=always owns this)"
  reset_and_exit
fi

listening=$(ss -tlnp 2>/dev/null | grep -c ':8100 ' || true)
if [[ "${listening:-0}" -eq 0 ]]; then
  log "unit active but no listening socket on :8100 -- restarting"
  systemctl restart "${UNIT}.service"
  reset_and_exit
fi

if curl -m 5 -sf -o /dev/null http://127.0.0.1:8100/health; then
  log "holding"
  reset_and_exit
fi

# /health didn't answer in time. Distinguish "busy serving a real client" from
# "hung with nobody home" via established connections on :8100.
established=$(ss -tn state established '( sport = :8100 or dport = :8100 )' 2>/dev/null | grep -c ':8100' || true)
established=${established:-0}

count=$(( $(cat "$STATE_FILE" 2>/dev/null || echo 0) + 1 ))
echo "$count" > "$STATE_FILE"

if [[ "$established" -gt 0 ]]; then
  if [[ "$count" -ge "$BUSY_THRESHOLD" ]]; then
    log "busy for $count consecutive probes with $established established connection(s) -- restarting"
    systemctl restart "${UNIT}.service"
    reset_and_exit
  fi
  log "holding: /health slow but $established established connection(s) present ($count/$BUSY_THRESHOLD)"
else
  if [[ "$count" -ge "$HANG_THRESHOLD" ]]; then
    log "probable hang: /health slow, no established connections, $count consecutive -- restarting"
    systemctl restart "${UNIT}.service"
    reset_and_exit
  fi
  log "holding: /health slow, no connections yet ($count/$HANG_THRESHOLD)"
fi

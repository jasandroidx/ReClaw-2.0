#!/usr/bin/env bash
# Watchdog for reclaw-mcp-bridge.service.
#
# reclaw-mcp-bridge is a single-worker streamable-http server: a slow tool
# call (e.g. `sitrep` / `project_sitrep`, which runs ~15 sequential checks
# including `openclaw doctor --lint`) blocks EVERY route, including /health,
# for 30-90+ seconds. A naive "restart on first failed probe" watchdog run
# every minute from cron was killing the bridge mid-request on almost every
# sitrep call (root-caused 2026-08-17). This script only restarts after
# THRESHOLD consecutive failed probes, so one busy-but-alive minute doesn't
# trigger a kill, while a genuinely hung/dead process still gets caught.
set -uo pipefail

STATE_FILE="/root/ReClaw-2.0/data/mcp_bridge_watchdog_fail_count"
THRESHOLD=3

if curl -m 5 -sf -o /dev/null http://127.0.0.1:8100/health; then
  echo 0 > "$STATE_FILE"
  exit 0
fi

count=$(( $(cat "$STATE_FILE" 2>/dev/null || echo 0) + 1 ))
echo "$count" > "$STATE_FILE"

if [[ "$count" -ge "$THRESHOLD" ]]; then
  logger -t reclaw-mcp-bridge-watchdog "restarting reclaw-mcp-bridge after $count consecutive failed /health probes"
  systemctl restart reclaw-mcp-bridge.service
  echo 0 > "$STATE_FILE"
fi

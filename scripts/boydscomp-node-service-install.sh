#!/usr/bin/env bash
# Run ON BoydsComp (Linux PC) as user sirboydimus (or your login).
# Installs OpenClaw node host as a user service → survives reboot/logout.
#
# Usage:
#   export OPENCLAW_GATEWAY_TOKEN='…'   # from fortress
#   bash boydscomp-node-service-install.sh
set -euo pipefail

# After Tailscale Serve put HTTPS on :18789, node hosts MUST use wss + --tls.
# MagicDNS name is preferred over raw Tailscale IP.
HOST="${OPENCLAW_GATEWAY_HOST:-openclaw.tail20a090.ts.net}"
PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
NAME="${OPENCLAW_NODE_DISPLAY_NAME:-Linux PC (boydscomp)}"
TLS="${OPENCLAW_GATEWAY_TLS:-1}"
if [[ "$TLS" == "1" || "$TLS" == "true" ]]; then
  URL="${OPENCLAW_GATEWAY_URL:-wss://${HOST}:${PORT}}"
  TLS_FLAG=(--tls)
else
  URL="${OPENCLAW_GATEWAY_URL:-ws://${HOST}:${PORT}}"
  TLS_FLAG=()
fi

if [[ -z "${OPENCLAW_GATEWAY_TOKEN:-}" ]]; then
  echo "ERROR: set OPENCLAW_GATEWAY_TOKEN first"
  echo "  ssh root@${HOST} 'cat /root/.openclaw/gateway-token-for-node.txt'"
  exit 1
fi

export OPENCLAW_GATEWAY_TOKEN
export OPENCLAW_GATEWAY_URL="$URL"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "ERROR: openclaw not on PATH. Install 2026.7.x first:"
  echo "  sudo npm install -g openclaw@2026.7.1"
  exit 1
fi

echo "=== openclaw version ==="
openclaw --version

echo "=== health ${HOST}:${PORT} (https if TLS) ==="
if [[ "$TLS" == "1" || "$TLS" == "true" ]]; then
  curl -skf --max-time 5 "https://${HOST}:${PORT}/health" || {
    echo "ERROR: cannot reach fortress gateway health over HTTPS"
    exit 1
  }
else
  curl -sf --max-time 5 "http://${HOST}:${PORT}/health" || {
    echo "ERROR: cannot reach fortress gateway health"
    exit 1
  }
fi
echo

echo "=== install node service ==="
openclaw node install \
  --host "$HOST" \
  --port "$PORT" \
  --display-name "$NAME" \
  "${TLS_FLAG[@]}" \
  --force

echo "=== start ==="
openclaw node start || true
openclaw node restart || true

echo "=== status ==="
openclaw node status || true

echo
echo "DONE. Leave this machine on the tailnet. On fortress check:"
echo "  docker exec openclaw-gateway openclaw nodes status"
echo
echo "If pairing is required again, message Fortress Grok: approve the linux node"

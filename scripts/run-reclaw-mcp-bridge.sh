#!/usr/bin/env bash
# HTTP MCP bridge — streamable-http on :8100 for Tailscale clients.
# Clients connect to: http://100.108.130.82:8100/mcp
# Health:            http://100.108.130.82:8100/health
set -euo pipefail
cd "$(dirname "$0")/.."
source /root/.env 2>/dev/null || true

export RECLAW_GATEWAY_TOKEN="${RECLAW_GATEWAY_TOKEN:-}"
export RECLAW_GATEWAY_URL="${RECLAW_GATEWAY_URL:-http://127.0.0.1:8000}"
export MCP_TRANSPORT=streamable-http

# Canonical Tailscale IP for this host (openclaw).
export TAILSCALE_IP="${TAILSCALE_IP:-$(tailscale ip -4 2>/dev/null || echo 100.108.130.82)}"
# Bind all interfaces so localhost healthchecks + tailnet IP both work.
# Clients must still use the Tailscale URL, not the public eth0 IP.
export FASTMCP_HOST="${FASTMCP_HOST:-0.0.0.0}"
export FASTMCP_PORT="${FASTMCP_PORT:-8100}"
export MCP_PUBLIC_MODE="${MCP_PUBLIC_MODE:-1}"

extra=""
if [[ -f data/mcp_tunnel_host.txt ]]; then
  extra="$(tr -d '[:space:]' < data/mcp_tunnel_host.txt)"
fi
export MCP_EXTRA_ALLOWED_HOSTS="${MCP_EXTRA_ALLOWED_HOSTS:-${TAILSCALE_IP},${TAILSCALE_IP}:${FASTMCP_PORT},127.0.0.1,localhost,openclaw.tail20a090.ts.net,${extra}}"

exec .venv/bin/python scripts/reclaw_platform_mcp_server.py

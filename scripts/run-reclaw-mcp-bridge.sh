#!/usr/bin/env bash
# HTTP MCP bridge for remote Grok/Gemini connectors (Tailscale-only).
set -euo pipefail
cd "$(dirname "$0")/.."
source /root/.env 2>/dev/null || true
export RECLAW_GATEWAY_TOKEN="${RECLAW_GATEWAY_TOKEN:-Darkis3552?}"
export RECLAW_GATEWAY_URL="${RECLAW_GATEWAY_URL:-http://127.0.0.1:8000}"
export MCP_TRANSPORT=streamable-http
export FASTMCP_HOST=127.0.0.1
export FASTMCP_PORT=8100
export MCP_PUBLIC_MODE="${MCP_PUBLIC_MODE:-1}"
if [[ -f data/mcp_tunnel_host.txt ]]; then
  export MCP_EXTRA_ALLOWED_HOSTS="$(cat data/mcp_tunnel_host.txt)"
fi
exec .venv/bin/python scripts/reclaw_platform_mcp_server.py
#!/usr/bin/env bash
# Tailnet serve routes for ReClaw stack (no public funnel — use cloudflared for grok.com).
set -euo pipefail

MCP_PORT="${FASTMCP_PORT:-8100}"
GATEWAY_PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
RECLAW_PORT="${RECLAW_API_PORT:-8000}"

tailscale serve --bg --set-path=/ "http://127.0.0.1:${GATEWAY_PORT}" 2>/dev/null || true
tailscale serve --bg --set-path=/reclaw "http://127.0.0.1:${RECLAW_PORT}" 2>/dev/null || true
tailscale serve --bg --set-path=/reclaw-mcp "http://127.0.0.1:${MCP_PORT}" 2>/dev/null || true

echo "[+] Tailnet serve (phone/laptop with Tailscale):"
tailscale serve status || true
echo "[+] Tailnet MCP: https://openclaw.tail20a090.ts.net/reclaw-mcp/mcp"
if [[ -f /root/ReClaw-2.0/data/mcp_public_url.txt ]]; then
  echo "[+] grok.com MCP: $(cat /root/ReClaw-2.0/data/mcp_public_url.txt)"
else
  echo "[!] grok.com MCP: start reclaw-mcp-tunnel.service (cloudflared)"
fi
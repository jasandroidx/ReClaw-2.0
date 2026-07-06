#!/usr/bin/env bash
# Capture cloudflared quick-tunnel URL for grok.com Custom Connector.
set -euo pipefail
cd "$(dirname "$0")/.."
sleep 3
url=$(journalctl -u reclaw-mcp-tunnel --no-pager -n 80 2>/dev/null | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1 || true)
if [[ -z "$url" ]]; then
  exit 0
fi
host="${url#https://}"
mkdir -p data
echo "${url}/mcp" >data/mcp_public_url.txt
echo "$host" >data/mcp_tunnel_host.txt
systemctl restart reclaw-mcp-bridge 2>/dev/null || true
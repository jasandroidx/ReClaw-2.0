#!/usr/bin/env bash
# Public MCP tunnel for grok.com Custom Connector (MCP-only — does not expose gateway/API).
set -euo pipefail
cd "$(dirname "$0")/.."

URL_FILE="data/mcp_public_url.txt"
HOST_FILE="data/mcp_tunnel_host.txt"
mkdir -p data

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Install cloudflared first" >&2
  exit 1
fi

# Parse tunnel URL from cloudflared stderr (quick tunnel logs to stderr).
cloudflared tunnel --url "http://127.0.0.1:8100" 2>&1 | while IFS= read -r line; do
  echo "$line"
  if [[ "$line" =~ https://[a-z0-9-]+\.trycloudflare\.com ]]; then
    url="${BASH_REMATCH[0]}"
    host="${url#https://}"
    echo "$url/mcp" >"$URL_FILE"
    echo "$host" >"$HOST_FILE"
    echo "[mcp-tunnel] grok.com connector URL: $url/mcp" >&2
    systemctl restart reclaw-platform-mcp 2>/dev/null || true
  fi
done
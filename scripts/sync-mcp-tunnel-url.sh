#!/usr/bin/env bash
# DEPRECATED quick-tunnel URL capture.
# Canonical public MCP is Tailscale Funnel (stable MagicDNS).
# Do NOT write trycloudflare hostnames into data/mcp_public_url.txt.
set -euo pipefail
cd "$(dirname "$0")/.."
FUNNEL="https://openclaw.tail20a090.ts.net:10000/rk7m2q9x/mcp"
mkdir -p data
# Always re-assert Funnel as public SOT if missing or trycloudflare
cur=""
if [[ -f data/mcp_public_url.txt ]]; then
  cur=$(tr -d "[:space:]" < data/mcp_public_url.txt)
fi
if [[ -z "$cur" || "$cur" == *trycloudflare* ]]; then
  echo "$FUNNEL" > data/mcp_public_url.txt
  echo "openclaw.tail20a090.ts.net" > data/mcp_tunnel_host.txt
  echo "sync-mcp-tunnel-url: enforced Funnel SOT -> $FUNNEL"
else
  echo "sync-mcp-tunnel-url: leaving SOT ($cur); quick tunnel disabled"
fi
exit 0

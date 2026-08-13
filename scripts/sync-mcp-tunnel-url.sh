#!/usr/bin/env bash
# Canonical public MCP = Funnel :443 secret path. Never trycloudflare.
set -euo pipefail
cd "$(dirname "$0")/.."
FUNNEL="https://openclaw.tail20a090.ts.net/rk7m2q9x/mcp"
mkdir -p data
echo "$FUNNEL" > data/mcp_public_url.txt
echo "openclaw.tail20a090.ts.net" > data/mcp_tunnel_host.txt
echo "sync-mcp-tunnel-url: enforced Funnel :443 SOT -> $FUNNEL"
exit 0

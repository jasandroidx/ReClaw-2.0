#!/usr/bin/env bash
# Ensure public MCP Funnel is on :443 with secret path only.
set -euo pipefail
# Free default 443 serve aliases that conflict with Funnel
tailscale serve --https=443 off 2>/dev/null || true
tailscale funnel --bg --https=443 --set-path=/rk7m2q9x http://127.0.0.1:8100
echo -n "https://openclaw.tail20a090.ts.net/rk7m2q9x/mcp" > /root/ReClaw-2.0/data/mcp_public_url.txt
echo "openclaw.tail20a090.ts.net" > /root/ReClaw-2.0/data/mcp_tunnel_host.txt
tailscale funnel status
echo "[+] public MCP: $(cat /root/ReClaw-2.0/data/mcp_public_url.txt)"

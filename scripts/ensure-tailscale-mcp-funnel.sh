#!/usr/bin/env bash
# HARD STOP 2026-08-15: public Funnel disabled (no HTTP auth on MCP).
# Do not re-enable until Jason explicitly asks after denylist + auth review.
echo "REFUSED: Funnel is off. See data/mcp_public_url.txt (disabled)." >&2
exit 1

# --- original below ---
#!/usr/bin/env bash
# Ensure public MCP Funnel is on :443 with secret path only.
#
# The secret path is NOT stored in this (public) repo. Export MCP_FUNNEL_PATH
# from .env before running, e.g. MCP_FUNNEL_PATH=xxxxxxxx ./ensure-tailscale-mcp-funnel.sh
set -euo pipefail
: "${MCP_FUNNEL_PATH:?set MCP_FUNNEL_PATH (secret Funnel path) in .env — never commit it}"
TSNET_HOST="${TAILSCALE_HOST:-openclaw.tail20a090.ts.net}"
# Free default 443 serve aliases that conflict with Funnel
tailscale serve --https=443 off 2>/dev/null || true
tailscale funnel --bg --https=443 --set-path="/${MCP_FUNNEL_PATH}" http://127.0.0.1:8100
echo -n "https://${TSNET_HOST}/${MCP_FUNNEL_PATH}/mcp" > /root/ReClaw-2.0/data/mcp_public_url.txt
echo "${TSNET_HOST}" > /root/ReClaw-2.0/data/mcp_tunnel_host.txt
tailscale funnel status
echo "[+] public MCP: $(cat /root/ReClaw-2.0/data/mcp_public_url.txt)"

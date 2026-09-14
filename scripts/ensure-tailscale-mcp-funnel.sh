#!/usr/bin/env bash
# HARD STOP 2026-08-15: public Funnel disabled (no HTTP auth on MCP).
# Do not re-enable until Jason explicitly asks after denylist + auth review.
echo "REFUSED: Funnel is off. See data/mcp_public_url.txt (disabled)." >&2
exit 1

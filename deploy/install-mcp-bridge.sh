#!/usr/bin/env bash
set -euo pipefail
UNIT=/root/ReClaw-2.0/deploy/reclaw-mcp-bridge.service
cp $UNIT /etc/systemd/system/reclaw-mcp-bridge.service
chmod 644 /etc/systemd/system/reclaw-mcp-bridge.service
chmod +x /root/ReClaw-2.0/scripts/run-reclaw-mcp-bridge.sh
systemctl daemon-reload
systemctl enable reclaw-mcp-bridge
systemctl stop reclaw-mcp-bridge 2>/dev/null || true
systemctl start reclaw-mcp-bridge
sleep 2 && systemctl is-active reclaw-mcp-bridge && echo "MCP_BRIDGE_UP" || echo "CHECK: journalctl -u reclaw-mcp-bridge -n 20"

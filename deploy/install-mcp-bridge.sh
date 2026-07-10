#!/usr/bin/env bash
# deploy/install-mcp-bridge.sh
# One-shot installer for the ReClaw MCP HTTP Bridge systemd service.
#
# Run on the Hetzner box as root:
#   bash /root/ReClaw-2.0/deploy/install-mcp-bridge.sh
#
# What it does:
#   1. Copies the systemd unit from deploy/ to /etc/systemd/system/
#   2. Reloads systemd
#   3. Enables (start-on-boot) and starts the service
#   4. Runs a quick health check against :8100
#
set -euo pipefail

UNIT_NAME="reclaw-mcp-bridge.service"
UNIT_SRC="$(dirname "$(realpath "$0")")/${UNIT_NAME}"
UNIT_DST="/etc/systemd/system/${UNIT_NAME}"
RECLAW_ROOT="/root/ReClaw-2.0"
MCP_PORT="${FASTMCP_PORT:-8100}"

echo "▶ ReClaw MCP Bridge — systemd installer"
echo "  Unit source : ${UNIT_SRC}"
echo "  Unit dest   : ${UNIT_DST}"
echo "  Project root: ${RECLAW_ROOT}"
echo ""

# Sanity checks
if [[ $EUID -ne 0 ]]; then
  echo "✗ Must run as root (sudo bash $0)" >&2
  exit 1
fi
if [[ ! -f "${UNIT_SRC}" ]]; then
  echo "✗ Unit file not found: ${UNIT_SRC}" >&2
  exit 1
fi
if [[ ! -f "${RECLAW_ROOT}/scripts/run-reclaw-mcp-bridge.sh" ]]; then
  echo "✗ Bridge script not found in ${RECLAW_ROOT}/scripts/" >&2
  exit 1
fi
if [[ ! -x "${RECLAW_ROOT}/.venv/bin/python" ]]; then
  echo "✗ venv not found at ${RECLAW_ROOT}/.venv — run 'pip install -r requirements.txt' first" >&2
  exit 1
fi

# Ensure the bridge script is executable
chmod +x "${RECLAW_ROOT}/scripts/run-reclaw-mcp-bridge.sh"

# Install the unit file
echo "▶ Installing unit file…"
cp "${UNIT_SRC}" "${UNIT_DST}"
chmod 644 "${UNIT_DST}"

# Reload systemd and enable
echo "▶ Reloading systemd daemon…"
systemctl daemon-reload

echo "▶ Enabling ${UNIT_NAME} (start on boot)…"
systemctl enable "${UNIT_NAME}"

# Stop any old instance first
systemctl stop "${UNIT_NAME}" 2>/dev/null || true

echo "▶ Starting ${UNIT_NAME}…"
systemctl start "${UNIT_NAME}"

# Wait a moment then check status
sleep 2
if systemctl is-active --quiet "${UNIT_NAME}"; then
  echo ""
  echo "✅ Service is running."
  systemctl status "${UNIT_NAME}" --no-pager -l
  echo ""
  # Quick connectivity check
  echo "▶ Health check on port ${MCP_PORT}…"
  if curl -sf --max-time 5 "http://127.0.0.1:${MCP_PORT}/health" > /dev/null 2>&1; then
    echo "✅ MCP Bridge is healthy on :${MCP_PORT}"
  else
    echo "⚠  HTTP probe failed on :${MCP_PORT} — check logs with:"
    echo "    journalctl -u ${UNIT_NAME} -n 50 --no-pager"
  fi
else
  echo "✗ Service failed to start. Logs:"
  journalctl -u "${UNIT_NAME}" -n 30 --no-pager >&2
  exit 1
fi

echo ""
echo "Done. To manage the service:"
echo "  systemctl status  ${UNIT_NAME}"
echo "  systemctl restart ${UNIT_NAME}"
echo "  journalctl -u ${UNIT_NAME} -f"

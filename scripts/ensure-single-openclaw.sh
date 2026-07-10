#!/usr/bin/env bash
# ReClaw: one OpenClaw gateway only — Docker compose service, not systemd/npm-global.
set -euo pipefail

USER_UNIT_DIR="${HOME}/.config/systemd/user"
USER_UNIT="${USER_UNIT_DIR}/openclaw-gateway.service"
USER_UNIT_DISABLED="${USER_UNIT_DIR}/openclaw-gateway.service.disabled-by-reclaw"
CANONICAL="docker:openclaw-gateway (compose)"
COMPOSE_FILE="${COMPOSE_FILE:-/root/ReClaw-2.0/docker-compose.yml}"

echo "[ensure-single-openclaw] canonical gateway: ${CANONICAL}"

# Kill the duplicate install path (openclaw gateway install → user systemd).
if systemctl --user is-active openclaw-gateway >/dev/null 2>&1; then
  echo "[!] Stopping rogue user systemd openclaw-gateway"
  systemctl --user stop openclaw-gateway || true
fi
if [[ -f "${USER_UNIT}" && ! -L "${USER_UNIT}" ]]; then
  echo "[!] Moving ${USER_UNIT} aside (re-run openclaw gateway install recreates it)"
  mv "${USER_UNIT}" "${USER_UNIT_DISABLED}.$(date +%s)"
  systemctl --user daemon-reload
fi
if ! systemctl --user is-enabled openclaw-gateway 2>/dev/null | grep -q masked; then
  systemctl --user disable openclaw-gateway 2>/dev/null || true
  systemctl --user mask openclaw-gateway 2>/dev/null || true
fi

# Port 18789: dual-stack loopback (127.0.0.1 + ::1) from one process is OK.
# Fail only when multiple distinct PIDs hold the port.
listeners=$(ss -tlnp 2>/dev/null | grep ':18789 ' || true)
if [[ -z "${listeners}" ]]; then
  echo "[!] Nothing listening on :18789 — start: cd /root/ReClaw-2.0 && docker compose up -d openclaw-gateway"
  exit 1
fi
pids=$(echo "${listeners}" | grep -oE 'pid=[0-9]+' | sed 's/pid=//' | sort -u)
pid_count=$(echo "${pids}" | grep -c '[0-9]' || true)
if [[ "${pid_count}" -gt 1 ]]; then
  echo "[!] MULTIPLE processes on :18789 — this breaks everything:"
  echo "${listeners}"
  exit 1
fi

# Docker container should own the port (host network).
if ! docker compose -f "${COMPOSE_FILE}" ps openclaw-gateway 2>/dev/null | grep -qE 'Up|running'; then
  echo "[!] Docker openclaw-gateway is not Up but something holds :18789"
  echo "${listeners}"
  exit 1
fi

if curl -sf http://127.0.0.1:18789/health >/dev/null; then
  echo "[+] Single OpenClaw gateway healthy on 127.0.0.1:18789 (${CANONICAL})"
  echo "    Android URL: wss://openclaw.tail20a090.ts.net"
else
  echo "[!] :18789 listener present but /health failed"
  exit 1
fi

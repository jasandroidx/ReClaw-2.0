#!/usr/bin/env bash
# Verify dual-path OpenClaw gateway reachability (Serve wss + lan fallback).
set -euo pipefail

MAGIC_DNS="${OPENCLAW_MAGIC_DNS:-openclaw.tail20a090.ts.net}"
TS_IP="$(tailscale ip -4 2>/dev/null || echo 100.85.152.115)"
PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
COMPOSE_FILE="${COMPOSE_FILE:-/root/ReClaw-2.0/docker-compose.yml}"
FAIL=0

ok() { echo "[OK] $*"; }
fail() { echo "[FAIL] $*"; FAIL=1; }

echo "=== OpenClaw Android path verify ==="

if docker compose -f "${COMPOSE_FILE}" ps openclaw-gateway 2>/dev/null | grep -qE 'Up|running'; then
  ok "docker openclaw-gateway Up"
else
  fail "docker openclaw-gateway not Up"
fi

if curl -sf --max-time 5 "http://127.0.0.1:${PORT}/health" | grep -q live; then
  ok "health loopback"
else
  fail "health loopback"
fi

if docker exec openclaw-gateway node -e "fetch('http://127.0.0.1:${PORT}/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" 2>/dev/null; then
  ok "health container"
else
  fail "health container"
fi

if curl -sfk --max-time 10 "https://${MAGIC_DNS}/health" | grep -q live; then
  ok "health MagicDNS https (Serve PRIMARY)"
else
  fail "health MagicDNS https (Serve PRIMARY)"
fi

if curl -sf --max-time 5 "http://${TS_IP}:${PORT}/health" | grep -q live; then
  ok "health Tailscale IP :${PORT} (lan FALLBACK)"
else
  fail "health Tailscale IP :${PORT} (lan FALLBACK)"
fi

if python3 - <<PY
import ssl, socket, base64, os, sys
host = "${MAGIC_DNS}"
origin = "https://localhost"
key = base64.b64encode(os.urandom(16)).decode()
req = (
    f"GET / HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
    f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\nOrigin: {origin}\r\n\r\n"
)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
raw = socket.create_connection((host, 443), timeout=10)
ss = ctx.wrap_socket(raw, server_hostname=host)
ss.sendall(req.encode())
line = ss.recv(4096).decode("utf-8", "replace").split("\r\n")[0]
ss.close()
print(line)
sys.exit(0 if "101" in line else 1)
PY
then
  ok "WSS 101 origin=https://localhost (Android)"
else
  fail "WSS 101 origin=https://localhost (Android)"
fi

if tailscale serve status 2>/dev/null | grep -q "127.0.0.1:${PORT}"; then
  ok "tailscale serve / → gateway"
else
  fail "tailscale serve / → gateway"
fi

if bash /root/ReClaw-2.0/scripts/ensure-single-openclaw.sh >/dev/null; then
  ok "single gateway process"
else
  fail "single gateway process"
fi

echo "---"
echo "PRIMARY Android:  wss://${MAGIC_DNS}"
echo "FALLBACK tailnet: ws://${TS_IP}:${PORT}"
echo "SOT: /root/ReClaw-2.0/data/openclaw_android_url.txt"
echo "PDANet: disconnect USB tether before pairing; use cellular + Tailscale."
if [[ "${FAIL}" -ne 0 ]]; then
  echo "RESULT: FAIL"
  exit 1
fi
echo "RESULT: OK"
exit 0

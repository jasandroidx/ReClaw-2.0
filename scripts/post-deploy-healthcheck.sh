#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[+] docker compose ps"
docker compose ps

echo "[+] reclaw-api health (8000)"
curl -sf http://127.0.0.1:8000/health | python3 -m json.tool

echo "[+] openclaw single-gateway guard"
bash scripts/ensure-single-openclaw.sh

echo "[+] openclaw gateway health (18789)"
curl -sf http://127.0.0.1:18789/health | python3 -m json.tool

echo "[+] ollama"
curl -sf http://127.0.0.1:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); print('models:', len(d.get('models',[])))" 2>/dev/null \
  || curl -sf http://127.0.0.1:8080/ | head -c 80; echo

echo "[+] fortress dashboard on 8081"
curl -sf http://127.0.0.1:8081/ | head -c 120 || true; echo
echo "[+] dashboard castle_map.json"
curl -sf http://127.0.0.1:8081/data/castle_map.json | python3 -c "import sys,json; d=json.load(sys.stdin); print('rooms:', len(d.get('rooms',[])))"

echo "[+] tailscale serve"
tailscale serve status || true

echo "[+] mcp bridge + public tunnel"
systemctl is-active reclaw-mcp-bridge reclaw-mcp-tunnel 2>/dev/null || true
if [[ -f data/mcp_public_url.txt ]]; then
  echo "grok.com URL: $(cat data/mcp_public_url.txt)"
  curl -sf -o /dev/null -w "public_mcp_http=%{http_code}\n" -X POST "$(cat data/mcp_public_url.txt)" \
    -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"hc","version":"1"}}}' || true
fi
openclaw mcp list 2>/dev/null || true

echo "[+] OK"
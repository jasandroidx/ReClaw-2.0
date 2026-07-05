#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[+] docker compose ps"
docker compose ps

echo "[+] reclaw-api health (8000)"
curl -sf http://127.0.0.1:8000/health | python3 -m json.tool

echo "[+] openclaw gateway health (18789)"
curl -sf http://127.0.0.1:18789/health | python3 -m json.tool

echo "[+] ollama on 8080"
curl -sf http://127.0.0.1:8080/ | head -c 80; echo

echo "[+] fortress dashboard on 8081"
curl -sf http://127.0.0.1:8081/ | head -c 120; echo
echo "[+] dashboard castle_map.json"
curl -sf http://127.0.0.1:8081/data/castle_map.json | python3 -c "import sys,json; d=json.load(sys.stdin); print('rooms:', len(d.get('rooms',[])))"

echo "[+] tailscale serve"
tailscale serve status || true

echo "[+] OK"
#!/usr/bin/env bash
sed -i 's/\r$//' "$0" 2>/dev/null || true
# Refresh dashboard/status.json from compose + loopback health.
# Never probes MCP :8100. Never invents room occupancy.
set -euo pipefail
ROOT="${ROOT:-/root/ReClaw-2.0}"
STATUS="$ROOT/dashboard/status.json"
WRITE=0
for a in "$@"; do
  case "$a" in
    --write) WRITE=1 ;;
    --root=*) ROOT="${a#--root=}"; STATUS="$ROOT/dashboard/status.json" ;;
  esac
done
cd "$ROOT"

now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
ps_json=$(docker compose ps --format json 2>/dev/null || true)

state_of() {
  local name="$1"
  echo "$ps_json" | python3 -c "
import json,sys
name=sys.argv[1]
raw=sys.stdin.read().strip()
if not raw:
    print('unknown'); raise SystemExit
items=[]
for line in raw.splitlines():
    line=line.strip()
    if not line: continue
    try:
        obj=json.loads(line)
        items.append(obj if isinstance(obj, dict) else obj)
    except Exception:
        pass
if raw.startswith('['):
    try: items=json.loads(raw)
    except Exception: pass
for o in items:
    n=(o.get('Name') or o.get('Service') or '')
    if n==name or o.get('Service')==name:
        s=(o.get('State') or o.get('Status') or '').lower()
        print('up' if ('running' in s or s=='running') else 'down')
        raise SystemExit
print('unknown')
" "$name"
}

probe() {
  local url="$1"
  curl -sS -m 2 -o /dev/null -w "%{http_code}" "$url" || echo 000
}

code8000=$(probe http://127.0.0.1:8000/health)
code8081=$(probe http://127.0.0.1:8081/)
code18789=$(probe http://127.0.0.1:18789/health)

api_state=$(state_of reclaw-api)
gw_state=$(state_of openclaw-gateway)
dash_state=$(state_of reclaw-dashboard)

api_ok=0; [ "$code8000" = "200" ] && api_ok=1
gw_ok=0; [ "$code18789" = "200" ] && gw_ok=1
dash_ok=0; [ "$code8081" = "200" ] && dash_ok=1

python3 - "$now" "$STATUS" "$WRITE" "$api_state" "$gw_state" "$dash_state" "$api_ok" "$gw_ok" "$dash_ok" "$code8000" "$code18789" "$code8081" <<'PY'
import json, os, sys, tempfile
from pathlib import Path
now, status, write, api_s, gw_s, dash_s, api_ok, gw_ok, dash_ok, c8000, c18789, c8081 = sys.argv[1:]
write = write == "1"
path = Path(status)
old = {}
if path.is_file():
    try:
        old = json.loads(path.read_text())
    except Exception:
        old = {}

def svc(ok, extra=None):
    d = {"status": "ok" if ok else "down"}
    if extra:
        d.update(extra)
    return d

out = {
    "generated_at": now,
    "network": "CONNECTED" if (api_ok == "1" and gw_ok == "1") else "DEGRADED",
    "network_detail": "compose+health",
    "data_source": "compose+health",
    "source": "compose+health",
    "agents_active": None,
    "rooms": [],
    "occupancy": "unknown",
    "services": {
        "reclaw_api": svc(api_ok == "1", {"env": "prod", "version": "2.0.0", "compose": api_s, "health_code": c8000}),
        "openclaw": {"ok": gw_ok == "1", "status": "live" if gw_ok == "1" else "down", "compose": gw_s, "health_code": c18789},
        "mcp": {"status": "unprobed", "service": "reclaw-platform", "transport": "streamable-http", "port": 8100, "note": "not probed"},
        "dashboard": {"status": "ok" if dash_ok == "1" else "down", "compose": dash_s, "health_code": c8081},
        "ollama_models": old.get("services", {}).get("ollama_models") if isinstance(old.get("services"), dict) else None,
    },
    "county_queue": old.get("county_queue"),
    "mcp_public_url_present": old.get("mcp_public_url_present"),
    "bridge": old.get("bridge"),
    "tunnel": old.get("tunnel"),
}
text = json.dumps(out, indent=2) + "\n"
print(text)
if not write:
    raise SystemExit(0)
path.parent.mkdir(parents=True, exist_ok=True)
bak = path.with_name(path.name + ".bak.20260903")
if path.is_file() and not bak.is_file():
    bak.write_text(path.read_text())
fd, tmp = tempfile.mkstemp(prefix="status.", suffix=".tmp", dir=str(path.parent))
os.write(fd, text.encode())
os.close(fd)
os.replace(tmp, path)
print("wrote", path, file=sys.stderr)
PY

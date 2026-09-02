#!/usr/bin/env bash
# Watch for pending OpenClaw device/node pairing and print IDs (optionally auto-approve).
# Usage:
#   bash scripts/linux-node-pair-watch.sh           # report only
#   bash scripts/linux-node-pair-watch.sh --approve  # approve pending device + node requests
set -euo pipefail
APPROVE=0
[[ "${1:-}" == "--approve" ]] && APPROVE=1

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) nodes status ==="
docker exec openclaw-gateway openclaw nodes status 2>/dev/null | tail -40 || true
echo
echo "=== devices list (pending + paired) ==="
docker exec openclaw-gateway openclaw devices list 2>/dev/null | tail -40 || true
echo
echo "=== nodes pending ==="
docker exec openclaw-gateway openclaw nodes pending 2>/dev/null | tail -30 || true

if [[ "$APPROVE" -eq 1 ]]; then
  echo
  echo "=== auto-approve pass (best-effort) ==="
  # Prefer JSON if available; fall back to human list + manual note
  if docker exec openclaw-gateway openclaw devices list --json >/tmp/oc-devices.json 2>/dev/null; then
    python3 - <<'PY'
import json, subprocess, sys
try:
    data=json.load(open("/tmp/oc-devices.json"))
except Exception as e:
    print("no json devices", e); sys.exit(0)
pending=[]
if isinstance(data, dict):
    pending=data.get("pending") or data.get("Pending") or []
    if not pending and "devices" in data:
        pending=[d for d in data["devices"] if d.get("status")=="pending" or d.get("pending")]
elif isinstance(data, list):
    pending=[d for d in data if (d.get("status") or "").lower()=="pending"]
for p in pending:
    rid=p.get("requestId") or p.get("id") or p.get("deviceId")
    print("approve device", rid, p.get("displayName") or p.get("name") or p.get("platform"))
    if rid:
        subprocess.run(["docker","exec","openclaw-gateway","openclaw","devices","approve",str(rid)], check=False)
PY
  fi
  if docker exec openclaw-gateway openclaw nodes pending --json >/tmp/oc-nodes-pending.json 2>/dev/null; then
    python3 - <<'PY'
import json, subprocess
try:
    data=json.load(open("/tmp/oc-nodes-pending.json"))
except Exception:
    data=[]
items=data if isinstance(data, list) else (data.get("pending") or data.get("requests") or [])
for p in items:
    rid=p.get("requestId") or p.get("id") or p.get("nodeId")
    print("approve node", rid, p.get("displayName") or p.get("name"))
    if rid:
        subprocess.run(["docker","exec","openclaw-gateway","openclaw","nodes","approve",str(rid)], check=False)
PY
  else
    echo "(nodes pending --json not available — run: openclaw nodes pending / nodes approve <id>)"
  fi
  echo
  echo "=== after approve ==="
  docker exec openclaw-gateway openclaw nodes status 2>/dev/null | tail -30 || true
fi

#!/usr/bin/env bash
# Bootstrap ReClaw orchestration layer on Hetzner.
set -euo pipefail
cd /root/ReClaw-2.0

echo "=== ReClaw Orchestration Bootstrap ==="

# OpenClaw gateway (Docker only)
docker compose ps openclaw-gateway 2>/dev/null | grep -q healthy && echo "OpenClaw: healthy" || {
  echo "Starting OpenClaw gateway..."
  docker compose up -d openclaw-gateway
}

# Total-ReClaw memory mount
PYTHONPATH=. .venv/bin/python -c "
from tools.total_reclaw_memory import mount_status, memory_save
s = mount_status()
print('Memory DB:', s['path'], 'count:', s['memory_count'])
if s['memory_count'] == 0:
    memory_save('ReClaw orchestration initialized on Hetzner.', county='', category='system', provenance='bootstrap_orchestration.sh')
    print('Seed memory written.')
"

# Stack health
curl -sf http://127.0.0.1:8000/health | head -c 120 && echo
curl -sf http://127.0.0.1:18789/health | head -c 80 && echo

echo "Orchestration map: data/reclaw_orchestration.yaml"
echo "County queue: curl -sf http://127.0.0.1:8000/county-queue/status"
echo "Default loop: Indiana 92-county queue (not Socrata SODA)."
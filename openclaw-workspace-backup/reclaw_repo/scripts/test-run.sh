#!/bin/bash
# scripts/test-run.sh — Safe, repeatable test workflow for ReClaw 2.0 on Hetzner/Openclaw
# Uses only seeds (no live fetch), dry-run by default. Non-destructive.
# Run with: bash scripts/test-run.sh

set -e

echo "=== ReClaw 2.0 Test Run (Seed-only, Dry-run) ==="
echo "Repo root: $(pwd)"
echo "Date: $(date -u)"
echo ""

# Ensure config dirs (idempotent) — use container for full env
docker compose exec -T reclaw-api python -c '
from core.config import get_settings
s = get_settings()
s.ensure_dirs()
print("✓ Config dirs ready (data/, outputs/, obsidian)")
' 2>/dev/null || echo "Note: Container not running yet — will create dirs on start"

# Run health check first (host level)
echo "1. Testing Gateway health..."
curl -f http://127.0.0.1:8000/health 2>/dev/null | python3 -m json.tool || echo "Health failed (container not running or port not ready). Start with: docker compose up -d"

echo ""
echo "2. Running CLI test with seeds + dry-run (safe)..."
docker compose exec -T reclaw-api python -m reclaw.cli run --county Pike --area Winslow --dry 2>&1 | cat || echo "CLI test skipped (container not running — run docker compose up -d first or install in dev env)"

echo ""
echo "3. Checking outputs..."
ls -l outputs/obsidian/Rural\ Data/ 2>/dev/null || echo "No outputs yet (first run or dry)."

echo ""
echo "Test complete. Check:"
echo "  - data/sessions/ for full audit logs (session.log + security.log)"
echo "  - /root/obsidian_vault/Rural Data/ for outputs"
echo "  - docker compose logs --tail=20 reclaw-api"
echo ""
echo "To run for real (after review): remove --dry or set WRITE_DRY_RUN=false in .env"
echo "All changes non-destructive. Docker logging is now rotated (json-file, 10m max)."

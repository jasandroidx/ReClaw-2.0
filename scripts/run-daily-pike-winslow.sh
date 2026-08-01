#!/usr/bin/env bash
# HARD FREEZE 2026-08-01 — Jason: no county auto packages without explicit unfreeze
FREEZE_FLAG="/root/ReClaw-2.0/data/RURAL_DATA_PIPELINE_FROZEN"
if [ -f "$FREEZE_FLAG" ]; then
  echo "$(date -Is) BLOCKED: rural data pipeline frozen. See $FREEZE_FLAG" | tee -a "${RECLAW_DAILY_LOG:-/var/log/reclaw-daily.log}"
  exit 0
fi
# Daily revenue loop: Pike/Winslow ContentPackage → Obsidian vault.
set -euo pipefail
cd "$(dirname "$0")/.."
LOG="${RECLAW_DAILY_LOG:-/var/log/reclaw-daily.log}"
# Refresh multi-year Gateway disbursements (skip if files exist)
./scripts/prefetch_gateway_years.sh >>"$LOG" 2>&1 || true
{
  echo "=== $(date -Is) daily Pike/Winslow ==="
  curl -sf -X POST "http://127.0.0.1:8000/run-sync?county=Pike&area=Winslow&write_obsidian=true"
  echo
} >>"$LOG" 2>&1
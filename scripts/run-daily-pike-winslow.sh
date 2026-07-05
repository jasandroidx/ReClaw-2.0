#!/usr/bin/env bash
# Daily revenue loop: Pike/Winslow ContentPackage → Obsidian vault.
set -euo pipefail
cd "$(dirname "$0")/.."
LOG="${RECLAW_DAILY_LOG:-/var/log/reclaw-daily.log}"
{
  echo "=== $(date -Is) daily Pike/Winslow ==="
  curl -sf -X POST "http://127.0.0.1:8000/run-sync?county=Pike&area=Winslow&write_obsidian=true"
  echo
} >>"$LOG" 2>&1
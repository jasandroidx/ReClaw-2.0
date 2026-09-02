#!/usr/bin/env bash
# Download Indiana Gateway disbursement files for multi-year red-flag analysis.
set -euo pipefail
cd "$(dirname "$0")/.."
CACHE="${RECLAW_GATEWAY_CACHE:-data/cache}"
mkdir -p "$CACHE"

for YEAR in 2022 2023 2024 2025; do
  OUT="$CACHE/gateway_disbursements_${YEAR}.txt"
  if [[ -f "$OUT" && "${FORCE:-0}" != "1" ]]; then
    echo "[skip] $OUT exists"
    continue
  fi
  echo "[fetch] disbursements $YEAR..."
  .venv/bin/python -c "
from pathlib import Path
from tools.indiana_gateway import download_disbursements
download_disbursements($YEAR, Path('$OUT'))
print('  →', '$OUT')
"
done
echo "[done] Gateway cache in $CACHE"
#!/usr/bin/env bash
# Prefetch statewide Indiana public data used by all 92 county audits.
set -euo pipefail
cd "$(dirname "$0")/.."
CACHE="${RECLAW_GATEWAY_CACHE:-data/cache}"
mkdir -p "$CACHE" data/cache/salaries

echo "[+] Gateway disbursements (2022-2025)"
./scripts/prefetch_gateway_years.sh

echo "[+] Gateway certified budget data (2022-2025)"
for YEAR in 2022 2023 2024 2025; do
  OUT="$CACHE/gateway_budget_data_${YEAR}.txt"
  if [[ -f "$OUT" && "${FORCE:-0}" != "1" ]]; then
    echo "[skip] $OUT"
    continue
  fi
  .venv/bin/python -c "
from pathlib import Path
from tools.indiana_gateway import download_budget_data
download_budget_data($YEAR, Path('$OUT'))
print('  →', '$OUT')
"
done

echo "[done] Indiana basics in $CACHE"
echo "[note] Per-county salary exports: Gateway Employee Compensation → data/cache/salaries/salary_{code}_{year}.csv"
#!/usr/bin/env bash
# Ingest reviewed assets from /root/DOGEGPT-20260615T020114Z-3-001
set -euo pipefail
SRC="/root/DOGEGPT-20260615T020114Z-3-001"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
ING="$REPO/ingestion"
DATA="$REPO/data/sources/indiana/pike"

mkdir -p "$ING" "$DATA/budget_orders" "$DATA/audit_reports" "$REPO/data/cache/dogegpt"

echo "[1/6] Pike CSVs (skip if identical)"
for f in pike_budget_textmode.csv pike_county_totals_2022_2025.csv; do
  cp -f "$SRC/Data/Indiana/Pike/$f" "$ING/$f"
done

echo "[2/6] Pipeline tooling + templates"
cp -f "$SRC/extract_pike_budget.py" "$ING/"
cp -f "$SRC/data_schema.csv" "$ING/"
cp -f "$SRC/video_script_template.md" "$ING/"
cp -f "$SRC/budget_anomaly_video_strategy.txt" "$ING/"
cp -f "$SRC/sources_anomaly_resources.md" "$ING/"

echo "[3/6] Pike budget-order + audit PDFs (provenance)"
cp -f "$SRC/Data/Indiana/Pike/Budget orders/"*.pdf "$DATA/budget_orders/" 2>/dev/null || true
cp -f "$SRC/Data/Indiana/Pike/Pike-"*.pdf "$DATA/budget_orders/" 2>/dev/null || true
cp -f "$SRC/Data/Indiana/Pike/Audit Reports/"*.pdf "$DATA/audit_reports/" 2>/dev/null || true

echo "[4/6] Symlink full upload (reference only — not duplicated)"
ln -sfn "$SRC" "$ING/dogegpt_upload"

echo "[5/6] Run merged anomaly pipeline on Pike data"
cd "$REPO"
PYTHONPATH=. .venv/bin/python "$ING/pipeline_budget_anomalies.py" \
  --in "$ING/pike_county_totals_2022_2025.csv" \
  --out "$ING/anomalies.csv" \
  --county "Pike County, IN"
PYTHONPATH=. .venv/bin/python "$ING/pipeline_budget_anomalies.py" \
  --in "$ING/pike_budget_textmode.csv" \
  --out "$ING/anomalies_pike_funds.csv" \
  --county "Pike County, IN"

echo "[6/6] Write manifest"
PYTHONPATH=. .venv/bin/python "$REPO/tools/dogegpt_ingest_manifest.py"

echo "[done] DOGEGPT ingest complete"
echo "[skip] Context/Pertinant Info/ (reference books — already in ingestion, copyright bloat)"
echo "[skip] Data/.ebaycreds (credentials — NEVER ingest)"
echo "[skip] DOGEGPT_AD_STARTER/ duplicate, anomaly-detection-resources-master/ duplicate"
echo "[skip] Empty Scripts/, Watchdog Reports/, Estimates/"
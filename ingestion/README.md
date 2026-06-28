# DOGEGPT – County Budget Anomaly Starter Kit

**Purpose:** Turn raw county budget/audit data into *flagged anomalies* you can script into viral watchdog videos.

## What’s inside
- `requirements.txt` – Python deps (PyOD, ADTK, pandas, etc.).
- `pipeline_budget_anomalies.py` – Run this on a CSV to generate `anomalies.csv`.
- `data_schema.csv` – Column spec & examples for your CSV.
- `sources_anomaly_resources.md` – Curated tools/datasets from the uploaded repo (only what’s useful here).
- `video_script_template.md` – Plug anomalies → audience-facing script beats.
- `.gitignore` – Keeps your repo clean.

## Quick start
```bash
# 1) Create a virtual env (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Install requirements
pip install -r requirements.txt

# 3) Put a CSV of budget line items somewhere (see data_schema.csv for format)

# 4) Run the pipeline
python pipeline_budget_anomalies.py --in data/pike_budget.csv --out output/anomalies.csv --county "Pike County, IN"
```

### Input CSV format (minimum)
See `data_schema.csv`, but the minimum useful columns are:
- `county` (e.g., Pike County, IN)
- `fiscal_year` (int, e.g., 2022), optional `month` (1–12) if you have monthly data
- `department` (e.g., Highway / Roads)
- `category` (e.g., Supplies / Capital Outlay)
- `account_code` or `gl_code`
- `amount` (numeric, positive for spend)
- optional: `vendor`, `description`

### What the pipeline does (overview)
1. **Cleans & normalizes** the data (types, outliers, duplicates, negatives).
2. **Time-series checks** per (department, category): robust z-scores, YoY spikes, ADTK detectors (if time granularity allows).
3. **Cross-sectional checks** within a year: Isolation Forest / PyOD on department totals + composition vectors.
4. **Emits** `anomalies.csv` with: keys, metrics, method, score, rationale, quick script line.

### Notes
- If ADTK isn’t applicable (no monthly/quarterly series), the script falls back to robust statistics + PyOD on annuals.
- For PDF budgets, convert to CSV first (use pdfplumber/Camelot/Tabula). We’ll wire that later once we have a real Pike PDF.
- Keep raw data untouched; write outputs to `output/`.

— Generated 2025-08-28.

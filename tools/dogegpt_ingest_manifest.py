"""Write manifest after DOGEGPT upload review + selective ingest."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from tools.public_data_loaders import REPO_ROOT

UPLOAD = Path("/root/DOGEGPT-20260615T020114Z-3-001")
MANIFEST = REPO_ROOT / "data" / "dogegpt_ingest_manifest.json"


def write_manifest() -> dict:
    ingested = {
        "pike_csvs": [
            "ingestion/pike_budget_textmode.csv",
            "ingestion/pike_county_totals_2022_2025.csv",
        ],
        "pipeline": "ingestion/pipeline_budget_anomalies.py",
        "extractor": "ingestion/extract_pike_budget.py",
        "templates": [
            "ingestion/video_script_template.md",
            "ingestion/budget_anomaly_video_strategy.txt",
            "ingestion/data_schema.csv",
        ],
        "pike_pdfs": "data/sources/indiana/pike/",
        "anomalies": [
            "ingestion/anomalies.csv",
            "ingestion/anomalies_pike_funds.csv",
        ],
        "upload_symlink": "ingestion/dogegpt_upload",
    }
    skipped = {
        "credentials": "Data/.ebaycreds — never ingest",
        "reference_books": "Context/Pertinant Info/ — copyright bloat, duplicates in ingestion/",
        "duplicates": [
            "DOGEGPT_AD_STARTER/ (copy of root kit)",
            "anomaly-detection-resources-master/ (already in ingestion/)",
        ],
        "empty_dirs": ["Scripts/", "Context/Watchdog Reports/", "Data/Indiana/Pike/Estimates/"],
    }
    manifest = {
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "upload_path": str(UPLOAD),
        "upload_size_bytes": sum(f.stat().st_size for f in UPLOAD.rglob("*") if f.is_file()),
        "file_count": sum(1 for _ in UPLOAD.rglob("*") if _.is_file()),
        "ingested": ingested,
        "skipped": skipped,
        "pipeline_note": (
            "Full AD_STARTER pipeline (ECOD, IsolationForest, robust z, ADTK) "
            "replaces simplified ReClaw stub; county-equal Gateway build via --county"
        ),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    m = write_manifest()
    print(json.dumps(m, indent=2))
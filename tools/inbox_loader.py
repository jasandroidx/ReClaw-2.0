"""
Scan data/inbox/ for user-dropped files and symlink or copy into ingestion/.

Human workflow: SCP huge CSVs/PDFs/zips to data/inbox/ → run scan → pipeline picks them up.

DOGEGPT zip (e.g. DOGEGPT-20260615T020114Z-3-001.zip):
  Extracts to data/inbox/extracted/<stem>/, copies data files to ingestion/,
  and if pipeline_budget_anomalies.py is present, registers the kit path.
"""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from tools.public_data_loaders import INGESTION, REPO_ROOT

INBOX = REPO_ROOT / "data" / "inbox"
MANIFEST = INBOX / "manifest.json"
EXTRACT_ROOT = INBOX / "extracted"
DOGEGPT_KIT = INGESTION / "dogegpt_kit"

SUPPORTED_SUFFIXES = {".csv", ".txt", ".pdf", ".json", ".xlsx", ".xls", ".zip", ".py", ".md"}
DATA_SUFFIXES = {".csv", ".txt", ".pdf", ".json", ".xlsx", ".xls"}


def scan_inbox(*, copy: bool = True) -> dict:
    """
    Process new files in data/inbox/. Returns manifest summary.
    Copies (default) or leaves in place with manifest entry pointing to path.
    """
    INBOX.mkdir(parents=True, exist_ok=True)
    INGESTION.mkdir(parents=True, exist_ok=True)

    manifest: dict = {"scanned_at": datetime.now(timezone.utc).isoformat(), "files": []}
    if MANIFEST.exists():
        try:
            manifest = json.loads(MANIFEST.read_text())
        except Exception:
            pass

    known = {f.get("name") for f in manifest.get("files", [])}
    new_count = 0

    # ⚡ Bolt: Use os.scandir() instead of Path.iterdir() for faster directory listing and cached stat() calls
    for entry in sorted(os.scandir(INBOX), key=lambda e: e.name):
        path_name = entry.name
        if path_name.startswith(".") or path_name in ("manifest.json", "extracted"):
            continue
        # We need the full path for path.suffix below, but entry doesn't have suffix directly
        path = INBOX / path_name
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue

        if path.suffix.lower() == ".zip":
            extract_dir = EXTRACT_ROOT / path.stem
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(extract_dir)
            copied = 0
            kit_registered = False
            is_dogegpt = "dogegpt" in path.name.lower()

            # Full DOGEGPT kit: mirror tree under ingestion/dogegpt_kit/
            if is_dogegpt or any(extract_dir.rglob("pipeline_budget_anomalies.py")):
                if DOGEGPT_KIT.exists():
                    shutil.rmtree(DOGEGPT_KIT)
                shutil.copytree(extract_dir, DOGEGPT_KIT, dirs_exist_ok=True)
                kit_registered = True

            for inner in extract_dir.rglob("*"):
                if not inner.is_file():
                    continue
                suf = inner.suffix.lower()
                if suf == ".zip":
                    continue
                if suf in DATA_SUFFIXES:
                    dest = INGESTION / inner.name
                    if copy and (not dest.exists() or inner.stat().st_mtime > dest.stat().st_mtime):
                        shutil.copy2(inner, dest)
                        copied += 1
                elif suf == ".py" and inner.name == "pipeline_budget_anomalies.py" and not kit_registered:
                    dest = INGESTION / inner.name
                    if copy:
                        shutil.copy2(inner, dest)
                        copied += 1

            entry = {
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "extracted_to": str(extract_dir),
                "files_copied_to_ingestion": copied,
                "dogegpt_kit": str(DOGEGPT_KIT) if kit_registered else None,
                "inbox_path": str(path),
                "action": "zip_extracted_dogegpt" if kit_registered else "zip_extracted",
                "registered_at": datetime.now(timezone.utc).isoformat(),
            }
            manifest.setdefault("files", []).append(entry)
            new_count += 1
            continue

        if path.name in known:
            continue

        dest = INGESTION / path.name
        if copy and not dest.exists():
            shutil.copy2(path, dest)
            action = "copied_to_ingestion"
        elif dest.exists():
            action = "already_in_ingestion"
        else:
            action = "registered_inbox_only"

        entry = {
            "name": path.name,
            "size_bytes": path.stat().st_size,
            "ingestion_path": str(dest) if dest.exists() else None,
            "inbox_path": str(path),
            "action": action,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        manifest.setdefault("files", []).append(entry)
        new_count += 1

    manifest["scanned_at"] = datetime.now(timezone.utc).isoformat()
    manifest["new_this_scan"] = new_count
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
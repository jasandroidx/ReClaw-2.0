"""
Scan data/inbox/ for user-dropped files and symlink or copy into ingestion/.

Human workflow: SCP huge CSVs/PDFs to data/inbox/ → run scan → pipeline picks them up.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from tools.public_data_loaders import INGESTION, REPO_ROOT

INBOX = REPO_ROOT / "data" / "inbox"
MANIFEST = INBOX / "manifest.json"

SUPPORTED_SUFFIXES = {".csv", ".txt", ".pdf", ".json", ".xlsx", ".xls"}


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

    for path in sorted(INBOX.iterdir()):
        if path.name.startswith(".") or path.name == "manifest.json":
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
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
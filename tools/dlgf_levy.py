"""
DLGF estimated maximum levy workbook download + county extract.

Source (public XLSX, no Firecrawl):
  https://www.in.gov/dlgf/county-specific-information/
  e.g. 2026 Estimated Maximum Levy Report

Use for: tax levy / max-levy contrast stories (wallet heat), not vendor fraud.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from tools.public_data_loaders import REPO_ROOT

CACHE = REPO_ROOT / "data" / "cache" / "dlgf"
# Verified 2026-07-17: HTTP 200, ~1.6MB xlsx
DEFAULT_LEVY_URL = (
    "https://www.in.gov/dlgf/files/2026-reports/2026-july-estimates/"
    "250714-2026-Estimated-Maximum-Levy.xlsx"
)


def download_max_levy_xlsx(url: str = DEFAULT_LEVY_URL) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    name = url.rstrip("/").split("/")[-1] or "max_levy.xlsx"
    dest = CACHE / name
    if dest.exists() and dest.stat().st_size > 10_000:
        return dest
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest


def extract_county_rows(county: str, *, path: Path | None = None) -> dict[str, Any]:
    """
    Best-effort read of max-levy workbook for one county name.
    Returns sheet rows that mention the county (openpyxl).
    """
    try:
        import openpyxl
    except ImportError as e:
        raise RuntimeError("openpyxl required: pip install openpyxl") from e

    path = path or download_max_levy_xlsx()
    name = county.replace(" County", "").strip().upper()
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    matches: list[dict[str, Any]] = []
    for sheet in wb.worksheets:
        headers: list[str] = []
        for i, row in enumerate(sheet.iter_rows(values_only=True)):
            vals = ["" if c is None else str(c).strip() for c in row]
            if i == 0 or (i < 5 and not headers):
                # detect header-ish row
                if any("county" in v.lower() or "unit" in v.lower() or "levy" in v.lower() for v in vals if v):
                    headers = vals
            joined = " ".join(vals).upper()
            if name and name in joined:
                rec = {"sheet": sheet.title, "row": vals[:40]}
                if headers:
                    rec["mapped"] = {
                        (headers[j] or f"col{j}"): vals[j]
                        for j in range(min(len(headers), len(vals)))
                        if headers[j] or vals[j]
                    }
                matches.append(rec)
            if len(matches) >= 80:
                break
        if len(matches) >= 80:
            break
    wb.close()

    out = {
        "county": county,
        "source_file": str(path.relative_to(REPO_ROOT)),
        "source_url": DEFAULT_LEVY_URL,
        "match_count": len(matches),
        "rows": matches[:50],
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
    slug = county.replace(" County", "").strip().lower().replace(" ", "_")
    out_path = CACHE / f"levy_{slug}.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    out["cache_path"] = str(out_path)
    return out


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("county", nargs="?", default="Clark")
    ap.add_argument("--download-only", action="store_true")
    args = ap.parse_args()
    p = download_max_levy_xlsx()
    print("xlsx", p, p.stat().st_size)
    if not args.download_only:
        print(json.dumps(extract_county_rows(args.county, path=p), indent=2)[:3000])

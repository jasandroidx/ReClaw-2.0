#!/usr/bin/env python3
"""Generate Viral Scribe HHVCTA JSON manifest from a county audit or flag JSON file."""

from __future__ import annotations

import argparse
import json
import sys

import yaml

from tools.county_gateway_audit import audit_county_gateway
from tools.public_data_loaders import REPO_ROOT
from tools.scriptwriter import _pick_lead_flag
from tools.viral_scribe import build_scribe_manifest, write_scribe_manifest


def _gateway_code(county: str) -> int | None:
    wl = REPO_ROOT / "data" / "indiana_county_worklist.yaml"
    data = yaml.safe_load(wl.read_text(encoding="utf-8")) or {}
    name = county.replace(" County", "").strip().lower()
    for row in data.get("counties", []):
        if str(row.get("name", "")).lower() == name:
            return int(row["gateway_code"])
    return None


def main() -> int:
    p = argparse.ArgumentParser(description="ReClaw Viral Scribe manifest generator")
    p.add_argument("--county", help="County name (e.g. Gibson)")
    p.add_argument("--flag-json", help="Path to JSON flag or audit report")
    p.add_argument("--index", type=int, default=1, help="Output file index")
    p.add_argument("--stdout", action="store_true", help="Print JSON to stdout only")
    args = p.parse_args()

    if args.flag_json:
        report = json.loads(open(args.flag_json, encoding="utf-8").read())
        county = args.county or report.get("county") or "County"
        if "category" in report:
            flag = report
        elif report.get("red_flags"):
            flag = report["red_flags"][0]
        else:
            print("No flag in JSON", file=sys.stderr)
            return 1
        manifest = build_scribe_manifest(
            flag,
            county=county,
            source=report.get("source", "Indiana Gateway public records"),
        )
    elif args.county:
        code = _gateway_code(args.county)
        if code is None:
            print(f"Unknown county: {args.county}", file=sys.stderr)
            return 1
        audit = audit_county_gateway(code, args.county.replace(" County", ""))
        lead = _pick_lead_flag(audit.red_flags)
        if not lead:
            print(f"No publishable flags for {args.county}", file=sys.stderr)
            return 1
        manifest = build_scribe_manifest(lead, county=audit.county)
    else:
        p.print_help()
        return 1

    if args.stdout:
        print(json.dumps(manifest, indent=2))
        return 0

    path = write_scribe_manifest(manifest, county=manifest["metadata"]["jurisdiction"], index=args.index)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
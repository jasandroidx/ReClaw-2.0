#!/usr/bin/env python3
"""Run Benford's Law analysis on a CSV column or Indiana Gateway county disbursements."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.benford_analysis import analyze_csv_column, analyze_amounts, format_report


def _gateway_amounts(county: str, year: int) -> list[float]:
    from tools.split_purchase_detector import load_county_disbursements

    rows = load_county_disbursements(county, year)
    return [float(r["amount"]) for r in rows if float(r.get("amount") or 0) > 0]


def main() -> int:
    p = argparse.ArgumentParser(description="Benford first-digit analysis (ReClaw)")
    p.add_argument("--file", help="CSV file path")
    p.add_argument("--column", help="Amount column name (with --file)")
    p.add_argument("--county", help="Indiana county name (Gateway disbursements)")
    p.add_argument("--year", type=int, default=2025)
    p.add_argument("--threshold", type=float, default=0.04, help="Per-digit abs threshold (default 0.04)")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of table")
    args = p.parse_args()

    if args.county:
        amounts = _gateway_amounts(args.county, args.year)
        result = analyze_amounts(amounts, abs_threshold=args.threshold)
        result["source"] = f"gateway_disbursements:{args.county}:{args.year}"
    elif args.file and args.column:
        result = analyze_csv_column(args.file, args.column, abs_threshold=args.threshold)
        result["source"] = args.file
    else:
        p.print_help()
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
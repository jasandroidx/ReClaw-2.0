#!/usr/bin/env python3
"""Export Gateway Employee Compensation CSVs for Indiana counties."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.gateway_salary_export import export_county_salary, prefetch_worklist_salaries


def main() -> int:
    p = argparse.ArgumentParser(description="Gateway salary export → data/cache/salaries/")
    p.add_argument("county", nargs="?", help="County name (e.g. Spencer). Omit for batch.")
    p.add_argument("--year", type=int, default=2025)
    p.add_argument("--force", action="store_true")
    p.add_argument("--limit", type=int, default=None, help="Batch: max counties")
    p.add_argument("--all", action="store_true", help="Batch all 92 counties")
    args = p.parse_args()

    if args.county:
        path, msg = export_county_salary(args.county, year=args.year, force=args.force)
        print(msg)
        return 0 if path else 1

    if args.all or args.limit:
        results = prefetch_worklist_salaries(year=args.year, limit=args.limit, skip_cached=not args.force)
        ok = sum(1 for r in results if r.get("status") in ("ok", "cached"))
        fail = len(results) - ok
        for r in results:
            print(f"{r['county']}: {r.get('message') or r.get('status')}")
        print(f"Done: {ok} ok/cached, {fail} failed")
        return 0 if fail == 0 else 1

    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3
"""Scrape Socrata SODA datasets → data/inbox/ (+ optional Benford)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.socrata_scraper import SocrataScraper, analyze_scrape, load_sources, save_scrape


def main() -> int:
    p = argparse.ArgumentParser(description="Socrata SODA municipal data scraper (ReClaw)")
    p.add_argument("domain", nargs="?", help="Portal domain (e.g. data.cityofchicago.org)")
    p.add_argument("dataset_id", nargs="?", help="Dataset ID (e.g. b6qw-zcvj)")
    p.add_argument("--output", type=Path, help="Output CSV (default: data/inbox/socrata_*.csv)")
    p.add_argument("--max", type=int, help="Max records")
    p.add_argument("--token", help="Socrata app token (or SOCRATA_APP_TOKEN env)")
    p.add_argument("--where", help="SODA $where filter (SoQL)")
    p.add_argument("--label", help="Filename label slug")
    p.add_argument("--benford", action="store_true", help="Run Benford on amount column after scrape")
    p.add_argument("--list", action="store_true", help="List datasets from data/socrata_sources.yaml")
    args = p.parse_args()

    if args.list:
        for d in load_sources():
            print(f"{d.get('id')}: {d.get('domain')} / {d.get('dataset_id')} — {d.get('jurisdiction')}")
        return 0

    if not args.domain or not args.dataset_id:
        p.print_help()
        return 1

    token = args.token or os.environ.get("SOCRATA_APP_TOKEN", "").strip() or None
    scraper = SocrataScraper(args.domain, args.dataset_id, app_token=token)
    df = scraper.fetch_all(max_records=args.max, where=args.where)

    if df.empty:
        print("[!] No data downloaded. Check domain, dataset ID, and token.")
        return 1

    manifest = save_scrape(
        df,
        domain=args.domain,
        dataset_id=args.dataset_id,
        output=args.output,
        label=args.label,
    )
    print(f"Saved {manifest['rows']} rows → {manifest['csv_path']}")
    print(f"Manifest: data/cache/socrata/ (amount_col={manifest.get('amount_column')})")

    if args.benford:
        analysis = analyze_scrape(manifest)
        if analysis.get("report"):
            print(analysis["report"])
        else:
            print(analysis.get("reason", "Benford skipped"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
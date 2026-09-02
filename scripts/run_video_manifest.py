#!/usr/bin/env python3
"""Generate Remotion HHVCTA video manifest (v2 scenes)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.video_manifest import generate_viral_manifest, write_manifest_file, MANIFEST_DIR


def main() -> int:
    p = argparse.ArgumentParser(description="Generate Remotion video manifest for Project ReClaw")
    p.add_argument("--city", "--county", dest="jurisdiction", required=True, help="Municipality name")
    p.add_argument("--anomaly", required=True, help="Anomaly type (Benfords Law, Split Purchases, salary_shock, …)")
    p.add_argument("--data", required=True, help="Data point (e.g. '$4,999' or 'Digit 5')")
    p.add_argument("--source", required=True, help="Data source label")
    p.add_argument("--output", type=Path, help="Output JSON path")
    p.add_argument("--hook", help="Override hook spoken script")
    p.add_argument("--finding", help="Override value/finding text")
    args = p.parse_args()

    manifest = generate_viral_manifest(
        args.jurisdiction,
        args.anomaly,
        args.data,
        args.source,
        hook_line=args.hook,
        finding=args.finding,
        category=args.anomaly.lower().replace(" ", "_"),
    )

    out = args.output
    if not out:
        slug = args.jurisdiction.replace(" ", "_").lower()
        out = MANIFEST_DIR / slug / f"manifest_{slug}.json"

    path = write_manifest_file(manifest, out)
    print(f"[+] Video manifest: {path}")
    print(f"[+] Schema: {manifest['schema']} · scenes: {len(manifest['scenes'])}")
    print("[+] Feed into Remotion Node.js app to render.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
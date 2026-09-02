#!/usr/bin/env python3
"""
Grok / operator entry: manifest JSON → Remotion MP4.

  PYTHONPATH=. .venv/bin/python scripts/run_remotion_orchestrator.py \\
    --manifest data/manifests/gibson/manifest_gibson.json

  PYTHONPATH=. .venv/bin/python scripts/run_remotion_orchestrator.py --county Gibson

  PYTHONPATH=. .venv/bin/python scripts/run_remotion_orchestrator.py --county Gibson --background
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.remotion_orchestrator import (
    manifest_paths_for_county,
    render_county_shorts,
    render_manifest,
)


def main() -> int:
    p = argparse.ArgumentParser(description="ReClaw Remotion orchestrator — JSON → MP4")
    p.add_argument("--manifest", "-m", help="Path to reclaw video manifest JSON")
    p.add_argument("--county", "-c", help="Render latest manifest(s) for county")
    p.add_argument("--output", "-o", help="Output MP4 path")
    p.add_argument("--limit", type=int, default=1, help="Max manifests when using --county")
    p.add_argument(
        "--background",
        action="store_true",
        help="Start render in background (returns PID immediately)",
    )
    p.add_argument("--list", action="store_true", help="List manifests for --county")
    args = p.parse_args()

    if args.list:
        if not args.county:
            print("--list requires --county", file=sys.stderr)
            return 1
        paths = manifest_paths_for_county(args.county)
        for path in paths:
            print(path)
        print(f"[{len(paths)} manifest(s)]")
        return 0

    if args.manifest:
        result = render_manifest(
            args.manifest,
            output_path=args.output,
            county=args.county,
            background=args.background,
        )
        print(json.dumps({
            "ok": result.ok,
            "manifest": str(result.manifest_path),
            "output": str(result.output_path) if result.output_path else None,
            "status": result.job.status,
            "pid": result.job.pid,
            "error": result.job.error,
        }, indent=2))
        return 0 if result.ok else 1

    if args.county:
        results = render_county_shorts(
            args.county,
            limit=args.limit,
            background=args.background,
        )
        for r in results:
            print(json.dumps({
                "ok": r.ok,
                "manifest": str(r.manifest_path),
                "output": str(r.output_path) if r.output_path else None,
                "status": r.job.status,
                "pid": r.job.pid,
            }))
        return 0 if all(r.ok for r in results) else 1

    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
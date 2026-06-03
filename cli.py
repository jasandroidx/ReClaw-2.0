"""
Simple CLI for ReClaw 2.0 (local dev + scripts).

Usage examples:
  python -m reclaw.cli run --county Pike --area Winslow
  python -m reclaw.cli run --county Pike --area Winslow --live
  python -m reclaw.cli run --county Pike --area Winslow --dry

This is a convenience wrapper around Orchestrator + session creation.
For production scheduled work, prefer the Gateway HTTP endpoints (/trigger or /run-sync).
"""

import argparse
from pathlib import Path

# Imports work when running:
#   cd reclaw && PYTHONPATH=. python -m reclaw.cli run ...
# or after `pip install -e .`
from core.config import get_settings
from agents.orchestrator import Orchestrator
from core.session import create_session
from core.security import SecurityManager


def main():
    parser = argparse.ArgumentParser(description="ReClaw 2.0 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Run full pipeline for one county/area")
    run_p.add_argument("--county", default="Pike")
    run_p.add_argument("--area", default="Winslow")
    run_p.add_argument("--live", action="store_true", help="Allow live fetches (will still hit gates unless --auto-approve)")
    run_p.add_argument("--auto-approve", action="store_true", help="Pre-grant medium risk actions for this run")
    run_p.add_argument("--dry", action="store_true", help="Do not actually write to Obsidian (log only)")
    run_p.add_argument("--no-obsidian", action="store_true", help="Skip Obsidian channel write entirely")

    args = parser.parse_args()

    settings = get_settings()

    if args.live:
        # Temporary override for this process
        settings.use_live_fetch = True

    print(f"[cli] Starting ReClaw run for {args.county}/{args.area}")
    print(f"[cli] live_fetch={settings.use_live_fetch}  auto_approve={args.auto_approve}  dry={args.dry}")

    # Always create a real session for audit (matches Gateway behavior)
    session, task = create_session(
        county=args.county,
        area=args.area,
        triggered_by="cli",
        auto_approve=args.auto_approve,
        write_to_obsidian=not args.no_obsidian,
    )

    sec = SecurityManager(session.base_dir, session.session_id)
    sec.grant("public_data_seed", "cli:auto")
    if args.auto_approve or settings.use_live_fetch:
        sec.grant("public_data_live_fetch", "cli:auto-approve", notes="granted via --auto-approve or --live flag")
    sec.grant("heuristic_analysis", "cli:auto")
    sec.grant("obsidian_write", "cli:auto")

    orch = Orchestrator(settings, session=session)
    pkg = orch.run_county(
        county=args.county,
        area=args.area,
        write_to_obsidian=not args.no_obsidian,
        dry_run=args.dry,
    )

    print("\n=== DONE ===")
    print(f"Package: {pkg.id}")
    print(f"Risk: {pkg.analysis.overall_risk_score}")
    print(f"Red flags: {len(pkg.analysis.red_flags)}")
    print(f"Obsidian file: {pkg.obsidian_filename or '(skipped)'}")
    print(f"Session: {session.session_id}  (see data/sessions/{session.session_id}/ )")
    print(f"Full artifact: data/runs/ (latest timestamped json)")


if __name__ == "__main__":
    main()

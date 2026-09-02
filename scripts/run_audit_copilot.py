#!/usr/bin/env python3
"""AuditCopilot — explain one county flag with statistical anchors."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.audit_copilot import county_disbursement_amounts, explain_flag, statistical_anchors
from tools.red_flag_engine import scan_all_red_flags


def main() -> int:
    p = argparse.ArgumentParser(description="AuditCopilot flag explanation")
    p.add_argument("--county", default="Gibson")
    p.add_argument("--use-llm", action="store_true", help="Call Ollama (else deterministic)")
    p.add_argument("--index", type=int, default=0, help="Flag index by severity rank")
    args = p.parse_args()

    scan = scan_all_red_flags(county=args.county)
    if not scan.red_flags:
        print("No flags.")
        return 1

    amounts = county_disbursement_amounts(args.county)
    anchors = statistical_anchors(amounts)
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    flags = sorted(scan.red_flags, key=lambda f: order.get(f.severity, 9))
    flag = flags[min(args.index, len(flags) - 1)]

    result = explain_flag(flag, county=args.county, anchors=anchors, use_llm=args.use_llm)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
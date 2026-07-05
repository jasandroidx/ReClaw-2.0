#!/usr/bin/env python3
"""One-off test for Indiana Gateway disbursement download."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.indiana_gateway import download_disbursements

out = Path("/tmp/gateway_disbursements_2023.txt")
path = download_disbursements(2023, out)
text = path.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()
pike = [l for l in lines if "pike" in l.lower()[:80]]
print(f"saved {path} ({len(lines)} lines, {len(pike)} pike-ish)")
if pike:
    print("sample:", pike[0][:240])
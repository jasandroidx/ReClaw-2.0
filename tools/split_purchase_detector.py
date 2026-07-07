"""
Split-purchase detector — IC 36-1-12-19 bid-threshold avoidance pattern.

Gateway disbursements lack transaction dates; we detect same-vendor (ent_name)
multiple sub-threshold lines in one fiscal year that combine above threshold.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from core.handoff import RedFlag
from tools.public_data_loaders import REPO_ROOT

SINGLE_TX_MAX = 49_999
MIN_COMBINED = 50_000
MIN_TX_COUNT = 2
SRC = "https://gateway.ifionline.org/public/download.aspx"

# Gateway ent_name is often a rollup, not a payee vendor.
ROLLUP_VENDORS = frozenset({"governmental activities", "business-type activities", "0", ""})


def _float(val: str) -> float:
    try:
        return float(str(val or "0").replace(",", ""))
    except ValueError:
        return 0.0


def load_county_disbursements(
    county_name: str,
    year: int,
    *,
    cache_dir: Path | None = None,
) -> list[dict]:
    cache = cache_dir or REPO_ROOT / "data" / "cache"
    path = cache / f"gateway_disbursements_{year}.txt"
    if not path.exists():
        return []

    rows: list[dict] = []
    name = county_name.replace(" County", "").strip().lower()
    with path.open(encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="|")
        for row in reader:
            cnty = (row.get("cnty_description") or "").strip().lower()
            if cnty != name:
                continue
            amt = _float(row.get("amount"))
            if amt <= 0:
                continue
            rows.append(
                {
                    "year": year,
                    "vendor": (row.get("ent_name") or row.get("unit_name") or "unknown").strip(),
                    "fund": (row.get("fund_name") or "").strip(),
                    "line": (row.get("disburse_name") or row.get("class_name") or "").strip(),
                    "amount": amt,
                }
            )
    return rows


def detect_split_purchases(
    county: str,
    year: int = 2024,
    *,
    cache_dir: Path | None = None,
) -> list[RedFlag]:
    """Flag vendors with multiple sub-threshold payments summing above bid threshold."""
    rows = load_county_disbursements(county, year, cache_dir=cache_dir)
    if not rows:
        return []

    by_vendor: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        vendor_key = (r["vendor"] or "").strip().lower()
        if vendor_key in ROLLUP_VENDORS:
            continue
        if r["amount"] < SINGLE_TX_MAX:
            by_vendor[r["vendor"]].append(r)

    flags: list[RedFlag] = []
    for vendor, txs in by_vendor.items():
        if len(txs) < MIN_TX_COUNT:
            continue
        total = sum(t["amount"] for t in txs)
        if total < MIN_COMBINED:
            continue
        flags.append(
            RedFlag(
                severity="high" if total >= 100_000 else "medium",
                category="split_purchase",
                description=(
                    f"{county} FY{year}: '{vendor}' received {len(txs)} disbursements "
                    f"each under ${SINGLE_TX_MAX:,}, totaling ${total:,.0f} — "
                    "possible bid-threshold splitting (IC 36-1-12-19 pattern)."
                ),
                evidence=json.dumps(
                    {
                        "vendor": vendor[:80],
                        "tx_count": len(txs),
                        "total": total,
                        "year": year,
                        "source": "gateway",
                        "statute": "IC 36-1-12-19",
                    }
                ),
                recommended_action="Request bid tabulation and purchase orders for this vendor/year.",
            )
        )
    return sorted(flags, key=lambda f: -json.loads(f.evidence).get("total", 0))[:10]
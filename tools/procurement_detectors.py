"""
Procurement-style detectors ported from sf-vendor-audit and audit-analytics-toolkit,
adapted for Indiana Gateway disbursement flat files.

Gateway limitation: ent_name is usually a fund/activity rollup (e.g. "Governmental
Activities"), NOT a payee vendor. Vendor-level duplicate-payment logic from
sf-vendor-audit does not apply without check registers or PO data.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from core.handoff import RedFlag
from tools.public_data_loaders import REPO_ROOT

SRC = "https://gateway.ifionline.org/public/download.aspx"

# Rollup labels — not real vendors; exclude from vendor-style tests.
ROLLUP_ENTITIES = frozenset(
    {
        "governmental activities",
        "business-type activities",
        "0",
        "",
    }
)


def _is_rollup_entity(name: str) -> bool:
    return (name or "").strip().lower() in ROLLUP_ENTITIES


def _load_disbursement_rows(
    county: str,
    year: int,
    *,
    cache_dir: Path | None = None,
) -> list[dict]:
    from tools.split_purchase_detector import load_county_disbursements

    cache = cache_dir or REPO_ROOT / "data" / "cache"
    raw = load_county_disbursements(county, year, cache_dir=cache)
    rows: list[dict] = []
    for r in raw:
        vendor = (r.get("vendor") or "").strip()
        rows.append(
            {
                "year": year,
                "vendor": vendor,
                "fund": (r.get("fund") or "").strip(),
                "line": (r.get("line") or "").strip(),
                "amount": float(r.get("amount") or 0),
                "is_rollup": _is_rollup_entity(vendor),
            }
        )
    return rows


def benford_mad(amounts: list[float]) -> dict:
    """Nigrini MAD first-digit test (shared with tools/benford_analysis.py)."""
    from tools.benford_analysis import analyze_amounts

    result = analyze_amounts(amounts)
    return {
        "n": result["n"],
        "mad": result["mad"],
        "verdict": result["verdict"],
        "suspicious_digit_count": result.get("suspicious_digit_count", 0),
        "digits": result.get("digits", []),
    }


def detect_iqr_outliers(
    county: str,
    year: int = 2025,
    *,
    cache_dir: Path | None = None,
    iqr_multiplier: float = 3.0,
    min_amount: float = 100_000,
    max_flags: int = 8,
) -> list[RedFlag]:
    """sf-vendor TEST 6 — row-level IQR outliers on disbursement lines."""
    rows = _load_disbursement_rows(county, year, cache_dir=cache_dir)
    positive = [r for r in rows if r["amount"] > 0]
    if len(positive) < 20:
        return []

    amts = np.array([r["amount"] for r in positive], dtype=float)
    q1, q3 = np.percentile(amts, [25, 75])
    fence = float(q3 + iqr_multiplier * (q3 - q1))

    flags: list[RedFlag] = []
    for r in sorted(positive, key=lambda x: -x["amount"]):
        if r["amount"] < max(fence, min_amount):
            continue
        flags.append(
            RedFlag(
                severity="high" if r["amount"] >= 1_000_000 else "medium",
                category="statistical_anomaly",
                description=(
                    f"{county} FY{year}: disbursement line '{r['line']}' = ${r['amount']:,.0f} "
                    f"exceeds IQR upper fence ${fence:,.0f} (3×IQR method)"
                ),
                evidence=json.dumps(
                    {
                        "amount": r["amount"],
                        "line": r["line"][:120],
                        "fund": r["fund"][:80],
                        "vendor_field": r["vendor"][:80],
                        "year": year,
                        "fence": fence,
                        "method": "IQR_3x",
                        "source": "gateway",
                    }
                ),
                recommended_action="Identify underlying payees in SBOA audit or county check register.",
            )
        )
        if len(flags) >= max_flags:
            break
    return flags


def detect_benford_mad(
    county: str,
    year: int = 2025,
    *,
    cache_dir: Path | None = None,
) -> list[RedFlag]:
    """Upgrade basic chi-sq Benford to Nigrini MAD verdict."""
    rows = _load_disbursement_rows(county, year, cache_dir=cache_dir)
    amounts = [r["amount"] for r in rows if r["amount"] > 0]
    stats = benford_mad(amounts)
    if stats["verdict"] not in ("marginal", "nonconforming"):
        return []

    sev = "high" if stats["verdict"] == "nonconforming" else "medium"
    return [
        RedFlag(
            severity=sev,
            category="benford_violation",
            description=(
                f"{county} FY{year}: disbursement amounts show Benford {stats['verdict']} "
                f"(MAD={stats['mad']}, n={stats['n']}) — smoke test only"
            ),
            evidence=f"Nigrini MAD Benford on Gateway disbursements; {SRC}",
            recommended_action="Forensic sample of disbursement supporting docs; not proof of fraud.",
        )
    ]


def detect_unit_sole_source(
    county: str,
    year: int = 2025,
    *,
    cache_dir: Path | None = None,
    min_unit_total: float = 250_000,
    concentration_pct: float = 0.50,
) -> list[RedFlag]:
    """
    sf-vendor TEST 4 adapted — but Gateway has no unit_name in split_purchase loader.
    Uses fund-level concentration when one disburse_name dominates a fund.
    """
    rows = _load_disbursement_rows(county, year, cache_dir=cache_dir)
    by_fund_line: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    fund_totals: dict[str, float] = defaultdict(float)

    for r in rows:
        if r["amount"] <= 0 or not r["fund"]:
            continue
        by_fund_line[r["fund"]][r["line"]] += r["amount"]
        fund_totals[r["fund"]] += r["amount"]

    flags: list[RedFlag] = []
    for fund, total in fund_totals.items():
        if total < min_unit_total:
            continue
        top_line, top_amt = max(by_fund_line[fund].items(), key=lambda x: x[1])
        share = top_amt / total
        if share >= concentration_pct and top_amt >= min_unit_total:
            flags.append(
                RedFlag(
                    severity="medium",
                    category="composition_outlier",
                    description=(
                        f"{county} FY{year}: fund '{fund}' — '{top_line}' is {share*100:.0f}% "
                        f"of fund disbursements (${top_amt:,.0f} / ${total:,.0f})"
                    ),
                    evidence=json.dumps(
                        {
                            "fund": fund[:80],
                            "line": top_line[:80],
                            "share": round(share, 3),
                            "amount": top_amt,
                            "year": year,
                            "source": "gateway",
                        }
                    ),
                    recommended_action="Compare fund mix to prior year and budget certification.",
                )
            )

    return sorted(flags, key=lambda f: -json.loads(f.evidence).get("amount", 0))[:6]


def detect_all_procurement(
    county: str,
    year: int = 2025,
    *,
    cache_dir: Path | None = None,
) -> list[RedFlag]:
    """Run Gateway-compatible procurement detectors."""
    flags: list[RedFlag] = []
    flags.extend(detect_iqr_outliers(county, year, cache_dir=cache_dir))
    flags.extend(detect_benford_mad(county, year, cache_dir=cache_dir))
    flags.extend(detect_unit_sole_source(county, year, cache_dir=cache_dir))
    return flags
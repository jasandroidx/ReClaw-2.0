"""
Gateway-only county audit — works for any Indiana county from statewide cache.

Produces RedFlags for scriptwriter / county queue without Pike-specific CSVs.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from io import StringIO
from pathlib import Path

from core.handoff import RedFlag
from tools.audit_adapter import AuditResult, COUNTY_CENSUS
from tools.public_data_loaders import REPO_ROOT

CACHE_DIR = REPO_ROOT / "data" / "cache"


def _load_county_rows(gateway_code: int, year: int = 2024) -> list[dict]:
    path = CACHE_DIR / f"gateway_disbursements_{year}.txt"
    if not path.exists():
        return []
    rdr = csv.DictReader(StringIO(path.read_text()), delimiter="|")
    rows = []
    for row in rdr:
        try:
            if int(row.get("cnty_cd", 0)) == gateway_code:
                rows.append(row)
        except ValueError:
            continue
    return rows


def _parse_amount(row: dict) -> float:
    try:
        return float(row.get("amount", 0) or 0)
    except ValueError:
        return 0.0


def audit_county_gateway(
    gateway_code: int,
    county_name: str,
    *,
    year: int = 2024,
    prior_year: int | None = 2023,
) -> AuditResult:
    """Audit one county from Gateway disbursement cache."""
    rows = _load_county_rows(gateway_code, year)
    flags: list[RedFlag] = []
    county_label = f"{county_name} County"

    if not rows:
        return AuditResult(
            county=county_label,
            red_flags=[
                RedFlag(
                    severity="medium",
                    category="data_gap",
                    description=f"No Gateway disbursement rows found for {county_label} FY{year}.",
                    evidence=f"gateway cache {year}, cnty_cd={gateway_code}",
                    recommended_action="Prefetch Gateway data or retry next year.",
                )
            ],
            census=COUNTY_CENSUS.get(county_name, {}),
        )

    total = sum(_parse_amount(r) for r in rows)
    by_line: dict[str, float] = defaultdict(float)
    by_vendor: dict[str, float] = defaultdict(float)
    for r in rows:
        line = (r.get("disburse_name") or r.get("class_name") or "unknown").strip()
        vendor = (r.get("ent_name") or r.get("unit_name") or "unknown").strip()
        amt = _parse_amount(r)
        by_line[line] += amt
        by_vendor[vendor] += amt

    top_line, top_line_amt = max(by_line.items(), key=lambda x: x[1])
    if top_line_amt > 0 and top_line_amt / max(total, 1) >= 0.15:
        flags.append(
            RedFlag(
                severity="high" if top_line_amt >= 1_000_000 else "medium",
                category="dominant_disbursement",
                description=f"{county_label} FY{year}: '{top_line}' = ${top_line_amt:,.0f} ({top_line_amt/total*100:.1f}% of ${total:,.0f} total)",
                evidence=f"gateway.ifionline.org disbursements {year}, cnty_cd={gateway_code}",
                recommended_action="Ask commissioners what this line item funded at the next public meeting.",
            )
        )

    if by_vendor:
        top_v, top_v_amt = max(by_vendor.items(), key=lambda x: x[1])
        share = top_v_amt / max(total, 1)
        if share >= 0.35 and top_v_amt >= 500_000:
            flags.append(
                RedFlag(
                    severity="high" if share >= 0.5 else "medium",
                    category="vendor_concentration",
                    description=f"'{top_v}' received ${top_v_amt:,.0f} ({share*100:.1f}% of county disbursements FY{year})",
                    evidence=f"Gateway ent_name aggregation, {county_label}",
                    recommended_action="Check bid/procurement records for vendor concentration.",
                )
            )

    if prior_year:
        prior_rows = _load_county_rows(gateway_code, prior_year)
        prior_total = sum(_parse_amount(r) for r in prior_rows)
        if prior_total > 0 and total > 0:
            chg = (total - prior_total) / prior_total * 100
            if abs(chg) >= 12:
                flags.append(
                    RedFlag(
                        severity="high" if abs(chg) >= 20 else "medium",
                        category="federal_spending_spike" if abs(chg) >= 20 else "disbursement_swing",
                        description=f"{county_label} total disbursements {prior_year}→{year}: {chg:+.1f}% (${prior_total:,.0f} → ${total:,.0f})",
                        evidence=f"Gateway YoY cnty_cd={gateway_code}",
                        recommended_action="Compare to budget certification and public meeting minutes.",
                    )
                )

    if not flags:
        flags.append(
            RedFlag(
                severity="low",
                category="baseline",
                description=f"{county_label} FY{year} total disbursements ${total:,.0f} — no dominant anomalies in quick scan.",
                evidence=f"Gateway {year}, {len(rows)} rows",
                recommended_action="Shorts-only unless deeper Silent Auditor run finds more.",
            )
        )

    return AuditResult(
        county=county_label,
        red_flags=flags,
        census=COUNTY_CENSUS.get(county_name, {}),
    )
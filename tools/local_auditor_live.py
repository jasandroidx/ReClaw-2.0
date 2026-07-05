"""
Live Indiana county auditor — Gateway disbursements + forensic pattern detectors.

Produces AuditResult red flags for scriptwriter / county queue / Silent Auditor.
Categories align with tools/scriptwriter.py (dominant_disbursement, benford_*, etc.).
"""

from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path

from core.handoff import RedFlag
from tools.audit_adapter import COUNTY_CENSUS
from tools.public_data_loaders import REPO_ROOT

GATEWAY_DL = "https://gateway.ifionline.org/public/download.aspx"
UA = {"User-Agent": "ReClaw/2.0 Local Auditor (+public records research)"}

CACHE_DIR = REPO_ROOT / "data" / "cache"

# Benford expected first-digit frequencies
_BENFORD = [0.301, 0.176, 0.125, 0.097, 0.079, 0.067, 0.058, 0.051, 0.046]


@dataclass
class AuditResult:
    county: str
    state: str = "IN"
    fips: str = ""
    gateway_code: int | None = None
    red_flags: list[RedFlag] = field(default_factory=list)
    census: dict = field(default_factory=dict)
    years_audited: list[int] = field(default_factory=list)
    total_rows: int = 0


def _fips_from_gateway(code: int) -> str:
    return f"18{2 * code - 1:03d}"


def _county_name_from_gateway(code: int) -> str | None:
    rows = _load_rows(code, 2024)
    if rows:
        return rows[0].get("cnty_description", "").strip()
    return None


def _load_rows(gateway_code: int, year: int) -> list[dict]:
    path = CACHE_DIR / f"gateway_disbursements_{year}.txt"
    if not path.exists():
        return []
    out = []
    for row in csv.DictReader(StringIO(path.read_text()), delimiter="|"):
        try:
            if int(row.get("cnty_cd", 0)) == gateway_code:
                out.append(row)
        except ValueError:
            continue
    return out


def _amount(row: dict) -> float:
    try:
        return float(row.get("amount", 0) or 0)
    except ValueError:
        return 0.0


def _benford_test(amounts: list[float]) -> tuple[float, bool]:
    """Return (max deviation, failed) for first-digit Benford test."""
    positives = [a for a in amounts if a >= 1.0]
    if len(positives) < 50:
        return 0.0, False
    counts = [0] * 9
    for a in positives:
        s = str(int(a))
        d = int(s[0])
        if 1 <= d <= 9:
            counts[d - 1] += 1
    n = sum(counts)
    if n < 50:
        return 0.0, False
    max_dev = 0.0
    for i, c in enumerate(counts):
        obs = c / n
        exp = _BENFORD[i]
        max_dev = max(max_dev, abs(obs - exp))
    # Rule of thumb: >0.05 max deviation or chi-like threshold
    failed = max_dev >= 0.055 or sum(abs(counts[i] / n - _BENFORD[i]) for i in range(9)) > 0.25
    return max_dev, failed


def _round_number_cluster(amounts: list[float]) -> int:
    """Count suspiciously round disbursements (>= $1000, ends 000)."""
    return sum(1 for a in amounts if a >= 1000 and int(a) % 1000 == 0)


def audit_county(
    state: str,
    fips: str,
    county_label: str,
    *,
    gateway_code: int | None = None,
    years: list[int] | None = None,
) -> AuditResult:
    """
    Full live audit for one Indiana county.

    county_label: e.g. "Pike County"
    fips: e.g. "18125" (optional if gateway_code provided)
    """
    state = state.upper()
    name = county_label.replace(" County", "").strip()

    if gateway_code is None and fips.startswith("18"):
        try:
            gateway_code = (int(fips) - 18000 + 1) // 2
        except ValueError:
            gateway_code = None

    if gateway_code is None:
        return AuditResult(
            county=county_label,
            state=state,
            fips=fips,
            red_flags=[
                RedFlag(
                    severity="medium",
                    category="data_gap",
                    description=f"Cannot resolve Gateway code for {county_label}.",
                    evidence=f"fips={fips}",
                )
            ],
        )

    if not fips:
        fips = _fips_from_gateway(gateway_code)

    years = years or [y for y in (2022, 2023, 2024, 2025) if (CACHE_DIR / f"gateway_disbursements_{y}.txt").exists()]
    if not years:
        years = [2024]

    flags: list[RedFlag] = []
    all_amounts: list[float] = []
    total_rows = 0
    year_totals: dict[int, float] = {}

    for year in years:
        rows = _load_rows(gateway_code, year)
        total_rows += len(rows)
        year_sum = sum(_amount(r) for r in rows)
        year_totals[year] = year_sum
        all_amounts.extend(_amount(r) for r in rows if _amount(r) > 0)

        if not rows:
            continue

        by_line: dict[str, float] = defaultdict(float)
        by_vendor: dict[str, float] = defaultdict(float)
        by_fund: dict[str, float] = defaultdict(float)
        for r in rows:
            amt = _amount(r)
            line = (r.get("disburse_name") or r.get("class_name") or "unknown").strip()
            vendor = (r.get("ent_name") or r.get("unit_name") or "unknown").strip()
            fund = (r.get("fund_name") or "unknown").strip()
            by_line[line] += amt
            by_vendor[vendor] += amt
            by_fund[fund] += amt

        total = max(year_sum, 1)

        # Dominant single line item (local — most relatable)
        if by_line:
            top_line, top_amt = max(by_line.items(), key=lambda x: x[1])
            share = top_amt / total
            if top_amt >= 250_000 and share >= 0.08:
                flags.append(
                    RedFlag(
                        severity="critical" if top_amt >= 5_000_000 else "high",
                        category="dominant_disbursement",
                        description=(
                            f"{county_label} FY{year}: '{top_line}' = ${top_amt:,.0f} "
                            f"({share*100:.1f}% of ${total:,.0f} disbursements)"
                        ),
                        evidence=(
                            f'{{"amount": {top_amt}, "year": {year}, "source": "gateway", '
                            f'"cnty_cd": {gateway_code}, "line": "{top_line[:80]}"}}'
                        ),
                        recommended_action="Ask commissioners to explain this line at a public meeting.",
                    )
                )

        # Vendor concentration
        if by_vendor:
            top_v, top_v_amt = max(by_vendor.items(), key=lambda x: x[1])
            vshare = top_v_amt / total
            if vshare >= 0.35 and top_v_amt >= 500_000:
                flags.append(
                    RedFlag(
                        severity="high" if vshare >= 0.5 else "medium",
                        category="vendor_concentration",
                        description=(
                            f"'{top_v}' received ${top_v_amt:,.0f} ({vshare*100:.1f}% of "
                            f"{county_label} FY{year} disbursements)"
                        ),
                        evidence=f"Gateway vendor aggregation cnty_cd={gateway_code} year={year}",
                        recommended_action="Review bid/procurement records for vendor concentration.",
                    )
                )

        # Fund composition outlier
        if len(by_fund) >= 3:
            top_fund, fund_amt = max(by_fund.items(), key=lambda x: x[1])
            fshare = fund_amt / total
            if fshare >= 0.45 and fund_amt >= 1_000_000:
                flags.append(
                    RedFlag(
                        severity="medium",
                        category="composition_outlier",
                        description=(
                            f"{county_label} FY{year}: fund '{top_fund}' holds ${fund_amt:,.0f} "
                            f"({fshare*100:.1f}% of all disbursements)"
                        ),
                        evidence=f"Gateway fund_name aggregation year={year}",
                        recommended_action="Compare fund mix to prior years and budget certification.",
                    )
                )

    # YoY total swing (federal_spending_spike category for scriptwriter priority)
    sorted_years = sorted(year_totals.keys())
    if len(sorted_years) >= 2:
        y0, y1 = sorted_years[-2], sorted_years[-1]
        t0, t1 = year_totals[y0], year_totals[y1]
        if t0 > 0:
            chg = (t1 - t0) / t0 * 100
            if abs(chg) >= 15:
                flags.append(
                    RedFlag(
                        severity="high" if abs(chg) >= 25 else "medium",
                        category="federal_spending_spike" if abs(chg) >= 25 else "disbursement_swing",
                        description=(
                            f"{county_label} total disbursements {y0}→{y1}: {chg:+.1f}% "
                            f"(${t0:,.0f} → ${t1:,.0f})"
                        ),
                        evidence=f'{{"amount": {abs(t1-t0)}, "total": {t1}, "year": {y1}}}',
                        recommended_action="Compare to certified budget and federal grant timing.",
                    )
                )

    # Benford on latest year amounts
    if all_amounts:
        dev, failed = _benford_test(all_amounts)
        if failed:
            flags.append(
                RedFlag(
                    severity="high",
                    category="benford_violation",
                    description=(
                        f"{county_label} disbursement amounts show Benford's Law deviation "
                        f"(max digit skew {dev:.3f} across {len(all_amounts)} payments)"
                    ),
                    evidence=f"Benford first-digit test on Gateway disbursements, cnty_cd={gateway_code}",
                    recommended_action="Forensic review of disbursement ledger — not proof of fraud, a smoke test.",
                )
            )

        rounds = _round_number_cluster(all_amounts)
        if rounds >= 25:
            flags.append(
                RedFlag(
                    severity="medium",
                    category="round_number_cluster",
                    description=(
                        f"{county_label}: {rounds} disbursements are suspiciously round "
                        f"(whole thousands of dollars)"
                    ),
                    evidence=f"Gateway amount pattern scan cnty_cd={gateway_code}",
                    recommended_action="Sample round-check payments for supporting documentation.",
                )
            )

    if not flags:
        flags.append(
            RedFlag(
                severity="low",
                category="baseline",
                description=f"{county_label}: quick forensic scan found no dominant patterns ({total_rows} rows).",
                evidence=f"Gateway years={years}",
            )
        )

    # De-dupe by category+description prefix
    seen: set[str] = set()
    unique: list[RedFlag] = []
    for f in flags:
        key = f"{f.category}:{f.description[:100]}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)

    return AuditResult(
        county=county_label,
        state=state,
        fips=fips,
        gateway_code=gateway_code,
        red_flags=unique,
        census=dict(COUNTY_CENSUS.get(name, {})),
        years_audited=years,
        total_rows=total_rows,
    )


def audit_county_by_name(county_name: str, *, gateway_code: int | None = None) -> AuditResult:
    """Convenience: audit by short name ('Pike') using worklist or FIPS formula."""
    if gateway_code is None:
        wl = REPO_ROOT / "data" / "indiana_county_worklist.yaml"
        if wl.exists():
            import yaml

            data = yaml.safe_load(wl.read_text())
            for c in data.get("counties", []):
                if c.get("name", "").lower() == county_name.lower():
                    gateway_code = c.get("gateway_code")
                    fips = c.get("fips", "")
                    return audit_county(
                        "IN",
                        fips,
                        f"{county_name} County",
                        gateway_code=gateway_code,
                    )
        gateway_code = None

    label = f"{county_name} County" if not county_name.endswith("County") else county_name
    short = label.replace(" County", "").strip()
    fips = _fips_from_gateway(gateway_code) if gateway_code else ""
    return audit_county("IN", fips, label, gateway_code=gateway_code)


def to_compliance_package(result: AuditResult):
    """Convert AuditResult → CompliancePackage for orchestrator handoff."""
    from core.handoff import CompliancePackage

    high = sum(1 for f in result.red_flags if f.severity in ("critical", "high"))
    risk = min(10.0, 2.0 + high * 1.8 + len(result.red_flags) * 0.4)
    return CompliancePackage(
        county=result.county.replace(" County", ""),
        red_flags=result.red_flags,
        overall_risk_score=round(risk, 1),
        summary=(
            f"Local auditor: {len(result.red_flags)} flags across "
            f"{len(result.years_audited)} years ({result.total_rows:,} rows)."
        ),
        source_file=str(CACHE_DIR),
        total_records_audited=result.total_rows,
    )
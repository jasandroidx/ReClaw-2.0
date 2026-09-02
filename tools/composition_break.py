"""
Composition-break + collective-anomaly detectors from DOGEGPT patterns.

Composition break: fund/category mix shifts sharply YoY without obvious policy event.
Collective anomaly: several related funds each spike moderately, summing to material change.
"""

from __future__ import annotations

from collections import defaultdict

from core.handoff import RedFlag
from tools.dogegpt_budget import build_county_budget_csv
from tools.indiana_county_budget import load_county_budget_rows


def _float(val) -> float:
    try:
        return float(str(val or "0").replace(",", ""))
    except ValueError:
        return 0.0


def _fund_totals_by_year(county: str, years: list[int], gateway_code: int | None) -> dict[int, dict[str, float]]:
    name = county.replace(" County", "").strip()
    out: dict[int, dict[str, float]] = {}
    for year in years:
        rows = load_county_budget_rows(name, gateway_code=gateway_code, year=year)
        rows = [r for r in rows if (r.get("unit_name") or "").upper() == f"{name.upper()} COUNTY"]
        funds: dict[str, float] = defaultdict(float)
        for r in rows:
            fund = (r.get("fund_description") or "unknown").strip()
            amt = _float(r.get("Total budget estimate_adopted"))
            if amt > 0:
                funds[fund] += amt
        if funds:
            out[year] = dict(funds)
    return out


def detect_composition_breaks(
    county: str,
    *,
    gateway_code: int | None = None,
    years: list[int] | None = None,
    mix_shift_pct: float = 15.0,
) -> list[RedFlag]:
    """Flag funds whose share of total certified budget jumped materially YoY."""
    years = years or [2023, 2024, 2025]
    by_year = _fund_totals_by_year(county, years, gateway_code)
    if len(by_year) < 2:
        return []

    flags: list[RedFlag] = []
    sorted_years = sorted(by_year.keys())
    for i in range(1, len(sorted_years)):
        y0, y1 = sorted_years[i - 1], sorted_years[i]
        t0 = sum(by_year[y0].values())
        t1 = sum(by_year[y1].values())
        if t0 <= 0 or t1 <= 0:
            continue
        all_funds = set(by_year[y0]) | set(by_year[y1])
        for fund in all_funds:
            share0 = by_year[y0].get(fund, 0) / t0 * 100
            share1 = by_year[y1].get(fund, 0) / t1 * 100
            shift = share1 - share0
            if abs(shift) >= mix_shift_pct and max(share0, share1) >= 5:
                flags.append(
                    RedFlag(
                        severity="medium" if abs(shift) < 25 else "high",
                        category="composition_break",
                        description=(
                            f"{county} {fund}: share of certified budget "
                            f"{share0:.1f}% → {share1:.1f}% ({shift:+.1f} pts) FY{y0}→{y1}."
                        ),
                        evidence=f"Gateway certified budget composition; FY{y0} vs FY{y1}",
                        recommended_action="Pull budget order PDF for that fund; check council votes.",
                    )
                )
    return flags[:12]


def detect_collective_anomalies(
    county: str,
    *,
    gateway_code: int | None = None,
    years: list[int] | None = None,
    moderate_yoy_min: float = 5.0,
    moderate_yoy_max: float = 14.0,
    min_funds: int = 3,
) -> list[RedFlag]:
    """
    Several funds each rise moderately YoY — pattern bigger than any single line.
    DOGEGPT 'collective anomalies' / reclassification wave signal.
    """
    years = years or [2023, 2024, 2025]
    by_year = _fund_totals_by_year(county, years, gateway_code)
    if len(by_year) < 2:
        return []

    flags: list[RedFlag] = []
    y0, y1 = sorted(by_year.keys())[-2], sorted(by_year.keys())[-1]
    moderate: list[tuple[str, float, float]] = []
    for fund in set(by_year[y0]) & set(by_year[y1]):
        prev, curr = by_year[y0][fund], by_year[y1][fund]
        if prev <= 0:
            continue
        pct = (curr - prev) / prev * 100
        if moderate_yoy_min <= pct <= moderate_yoy_max:
            moderate.append((fund, prev, curr))

    if len(moderate) >= min_funds:
        total_delta = sum(c - p for _, p, c in moderate)
        names = ", ".join(f[0][:30] for f in moderate[:4])
        flags.append(
            RedFlag(
                severity="medium",
                category="collective_anomaly",
                description=(
                    f"{county} FY{y0}→{y1}: {len(moderate)} funds each rose "
                    f"{moderate_yoy_min:.0f}–{moderate_yoy_max:.0f}% YoY, "
                    f"combined +${total_delta:,.0f} ({names}…)."
                ),
                evidence="Gateway fund-level certified budgets; collective moderate spikes",
                recommended_action="Investigate reclassification wave or vendor steering across related funds.",
            )
        )
    return flags
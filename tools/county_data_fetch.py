"""
Fetch all public data layers for any Indiana county (no Pike special-casing).

Layers:
  1. Gateway certified budgets (statewide file → county filter)
  2. Gateway disbursements (statewide cache → county filter)
  3. Gateway salaries (per-county export cache / inbox)
  4. Live APIs via local_auditor_live (USASpending, Census, ProPublica)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from core.handoff import BudgetData, SalaryEntry, SourceRef
from tools.indiana_county_budget import load_county_budget_totals_series, load_county_budgets
from tools.indiana_gateway_salary import load_county_salary_records, load_county_salaries
from tools.public_data_loaders import REPO_ROOT, gateway_disbursement_stats
from tools.indiana_gateway import download_disbursements


@dataclass
class CountyDataBundle:
    county: str
    gateway_code: int
    fips: str
    budgets: list[BudgetData] = field(default_factory=list)
    budget_series: list[dict] = field(default_factory=list)
    salaries: list[SalaryEntry] = field(default_factory=list)
    salary_records: list[dict] = field(default_factory=list)
    sources: list[SourceRef] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    gateway_stats: dict = field(default_factory=dict)


def resolve_county(county_name: str) -> dict | None:
    """Look up gateway_code + fips from worklist."""
    wl = REPO_ROOT / "data" / "indiana_county_worklist.yaml"
    if not wl.exists():
        return None
    data = yaml.safe_load(wl.read_text())
    for c in data.get("counties", []):
        if c.get("name", "").lower() == county_name.replace(" County", "").strip().lower():
            return c
    return None


def fetch_county_data(
    county_name: str,
    *,
    gateway_code: int | None = None,
    fips: str | None = None,
    years: list[int] | None = None,
) -> CountyDataBundle:
    """Pull every automated layer for one county."""
    name = county_name.replace(" County", "").strip()
    meta = resolve_county(name) or {}
    gateway_code = gateway_code or meta.get("gateway_code")
    fips = fips or meta.get("fips", "")

    if not gateway_code:
        return CountyDataBundle(
            county=name,
            gateway_code=0,
            fips=fips or "",
            gaps=[f"Unknown gateway_code for {name}"],
        )

    years = years or [2025, 2024, 2023, 2022]
    bundle = CountyDataBundle(county=name, gateway_code=gateway_code, fips=fips)

    budgets, b_src = load_county_budgets(name, gateway_code=gateway_code, years=years)
    bundle.budgets = budgets
    bundle.budget_series = load_county_budget_totals_series(
        name, gateway_code=gateway_code, years=years
    )
    bundle.sources.extend(b_src)
    if not budgets:
        bundle.gaps.append("Gateway certified budget rows missing for this county/year")

    salaries, s_src, records = load_county_salaries(
        name, gateway_code=gateway_code, year=max(years)
    )
    bundle.salaries = salaries
    bundle.salary_records = records
    bundle.sources.extend(s_src)
    if not records:
        bundle.gaps.append(
            f"Salary export not cached — export from Gateway Employee Compensation "
            f"→ data/cache/salaries/salary_{gateway_code}_{max(years)}.csv"
        )

    cache_dir = REPO_ROOT / "data" / "cache"
    year = max(years)
    disb_path = cache_dir / f"gateway_disbursements_{year}.txt"
    if not disb_path.exists():
        try:
            download_disbursements(year, disb_path)
        except Exception as e:
            bundle.gaps.append(f"Gateway disbursement download failed: {e}")

    if disb_path.exists():
        stats, _ = gateway_disbursement_stats(disb_path, county_name=name)
        bundle.gateway_stats = stats
        bundle.sources.append(
            SourceRef(
                kind="web",
                url="https://gateway.ifionline.org/public/download.aspx",
                note=f"Gateway disbursements {year}",
            )
        )

    return bundle
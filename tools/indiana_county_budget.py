"""
Indiana county certified budget loader — Gateway 'Budget Data' flat file.

Works for all 92 counties: one statewide download per year, filter by cnty_cd.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from io import StringIO
from pathlib import Path

from core.handoff import BudgetData, SourceRef
from tools.indiana_gateway import download_budget_data
from tools.public_data_loaders import REPO_ROOT

CACHE_DIR = REPO_ROOT / "data" / "cache"
BUDGET_CACHE = CACHE_DIR / "gateway_budget_data_{year}.txt"


def _budget_cache_path(year: int) -> Path:
    return CACHE_DIR / f"gateway_budget_data_{year}.txt"


def ensure_budget_file(year: int, *, force: bool = False) -> Path:
    path = _budget_cache_path(year)
    if path.exists() and path.stat().st_size > 10_000 and not force:
        return path
    return download_budget_data(year, path)


def _float(val: str | None) -> float:
    try:
        return float(str(val or "0").replace(",", ""))
    except ValueError:
        return 0.0


def load_county_budget_rows(
    county_name: str,
    *,
    gateway_code: int | None = None,
    year: int = 2025,
) -> list[dict]:
    """Raw budget rows for one county from Gateway budget file."""
    path = ensure_budget_file(year)
    name = county_name.replace(" County", "").strip().upper()
    rows: list[dict] = []

    for row in csv.DictReader(path.open(encoding="utf-8", errors="replace"), delimiter="|"):
        cnty = (row.get("cnty_description") or "").strip().upper()
        code = str(row.get("cnty_cd", "")).strip()
        if gateway_code is not None and code == str(gateway_code):
            rows.append(row)
        elif cnty == name:
            rows.append(row)
    return rows


def load_county_budgets(
    county_name: str,
    *,
    gateway_code: int | None = None,
    years: list[int] | None = None,
    county_unit_only: bool = True,
) -> tuple[list[BudgetData], list[SourceRef]]:
    """
    BudgetData entries for any Indiana county from Gateway certified budget file.
    """
    years = years or [2025, 2024, 2023, 2022]
    sources = [
        SourceRef(
            kind="web",
            url="https://gateway.ifionline.org/public/download.aspx",
            note="Gateway Budget Data flat file (DLGF certified estimates)",
        )
    ]
    budgets: list[BudgetData] = []
    name = county_name.replace(" County", "").strip()

    for year in years:
        rows = load_county_budget_rows(name, gateway_code=gateway_code, year=year)
        if not rows:
            continue

        if county_unit_only:
            rows = [r for r in rows if (r.get("unit_name") or "").upper() == f"{name.upper()} COUNTY"]

        by_fund: dict[str, float] = defaultdict(float)
        nav = 0.0
        for r in rows:
            fund = (r.get("fund_description") or "unknown").strip()
            adopted = _float(r.get("Total budget estimate_adopted") or r.get("Necessary expenditures_adopted"))
            by_fund[fund] += adopted
            nav = max(nav, _float(r.get("Net Assessed Valuation")))

        total = sum(by_fund.values())
        if total <= 0:
            continue

        budgets.append(
            BudgetData(
                fiscal_year=year,
                entity=f"{name} County",
                total_expenditures=int(total),
                major_funds={k: int(v) for k, v in sorted(by_fund.items(), key=lambda x: -x[1])[:12]},
                notes=(
                    f"Gateway certified budget FY{year}: {len(rows)} fund lines, "
                    f"NAV ${nav:,.0f}."
                ),
                source=sources[0],
            )
        )

    return budgets, sources


def load_county_budget_totals_series(
    county_name: str,
    *,
    gateway_code: int | None = None,
    years: list[int] | None = None,
) -> list[dict]:
    """YoY certified totals for county unit (for anomaly pipeline)."""
    years = years or [2022, 2023, 2024, 2025]
    series: list[dict] = []
    name = county_name.replace(" County", "").strip()

    for year in years:
        rows = load_county_budget_rows(name, gateway_code=gateway_code, year=year)
        rows = [r for r in rows if (r.get("unit_name") or "").upper() == f"{name.upper()} COUNTY"]
        total = sum(_float(r.get("Total budget estimate_adopted")) for r in rows)
        if total > 0:
            series.append({"year": year, "amount": int(total)})

    series.sort(key=lambda x: x["year"])
    for i in range(1, len(series)):
        prev = series[i - 1]["amount"]
        if prev > 0:
            series[i]["yoy_pct"] = round((series[i]["amount"] - prev) / prev * 100, 1)
    return series
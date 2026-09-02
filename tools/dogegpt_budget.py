"""
Build DOGEGPT-compatible budget CSV from Gateway certified data (any IN county).
"""

from __future__ import annotations

import csv
from pathlib import Path

from tools.county_data_fetch import resolve_county
from tools.indiana_county_budget import load_county_budget_rows
from tools.public_data_loaders import INGESTION, REPO_ROOT

CACHE_CSV = REPO_ROOT / "data" / "cache" / "dogegpt_budgets"


def _float(val: str | None) -> float:
    try:
        return float(str(val or "0").replace(",", ""))
    except ValueError:
        return 0.0


def build_county_budget_csv(
    county: str,
    *,
    years: list[int] | None = None,
    gateway_code: int | None = None,
) -> Path | None:
    """
    Export fund-level certified budget rows to DOGEGPT schema CSV.
    Returns path or None if no rows.
    """
    name = county.replace(" County", "").strip()
    meta = resolve_county(name) or {}
    gateway_code = gateway_code or meta.get("gateway_code")
    years = years or [2022, 2023, 2024, 2025]
    label = f"{name} County, IN"
    dept_label = f"{name.upper()} COUNTY"

    CACHE_CSV.mkdir(parents=True, exist_ok=True)
    out = CACHE_CSV / f"{name.lower()}_budget_{min(years)}_{max(years)}.csv"

    rows_out: list[dict] = []
    for year in years:
        raw = load_county_budget_rows(name, gateway_code=gateway_code, year=year)
        raw = [r for r in raw if (r.get("unit_name") or "").upper() == f"{name.upper()} COUNTY"]
        for r in raw:
            amt = _float(r.get("Total budget estimate_adopted") or r.get("Necessary expenditures_adopted"))
            if amt <= 0:
                continue
            fund = (r.get("fund_description") or "unknown").strip()
            rows_out.append(
                {
                    "county": label,
                    "fiscal_year": year,
                    "department": dept_label,
                    "category": fund,
                    "account_code": (r.get("fund_cd") or "").strip(),
                    "amount": int(amt),
                }
            )

        # County total row (for YoY on aggregate — matches Pike totals CSV)
        total = sum(row["amount"] for row in rows_out if row["fiscal_year"] == year)
        if total > 0:
            rows_out.append(
                {
                    "county": label,
                    "fiscal_year": year,
                    "department": dept_label,
                    "category": "TOTAL",
                    "account_code": "0000",
                    "amount": total,
                }
            )

    if not rows_out:
        return None

    fieldnames = ["county", "fiscal_year", "department", "category", "account_code", "amount"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)
    return out


def run_county_anomalies(
    county: str,
    *,
    out_path: Path | None = None,
) -> tuple[Path | None, int]:
    """Build CSV + run DOGEGPT pipeline; returns (anomalies_path, count)."""
    import sys

    csv_path = build_county_budget_csv(county)
    if not csv_path:
        return None, 0

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "pipeline_budget_anomalies",
        INGESTION / "pipeline_budget_anomalies.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    out = out_path or (INGESTION / f"anomalies_{county.lower()}.csv")
    n = mod.run_pipeline(csv_path, out, county=county)
    return out, n
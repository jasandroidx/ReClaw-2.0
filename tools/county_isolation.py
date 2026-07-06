"""
County data isolation — Pike ingestion files NEVER apply to other counties.

DOGEGPT model:
  Pike (bootstrap): manual Gateway exports in ingestion/ (SalarySearch.csv,
    pike_county_totals_2022_2025.csv, pike_budget_textmode.csv) + pipeline code.
  All other counties: statewide Gateway cache → tools/dogegpt_budget.py builds
    per-county CSV → anomalies_{county}.csv. Salaries via gateway_salary_export.
"""

from __future__ import annotations

from pathlib import Path

from tools.public_data_loaders import INGESTION, REPO_ROOT

PIKE_ONLY_INGESTION = frozenset(
    {
        "SalarySearch.csv",
        "pike_county_totals_2022_2025.csv",
        "pike_budget_textmode.csv",
        "anomalies.csv",
        "anomalies_pike.csv",
        "anomalies_pike_funds.csv",
    }
)


def normalize_county(name: str) -> str:
    return name.replace(" County", "").strip()


def is_pike(county: str) -> bool:
    return normalize_county(county).lower() == "pike"


def county_label(county: str) -> str:
    n = normalize_county(county)
    return f"{n} County, IN"


def county_department(county: str) -> str:
    return f"{normalize_county(county).upper()} COUNTY"


def pike_ingestion_path(filename: str) -> Path | None:
    """Return ingestion path only when filename is Pike-scoped and county is Pike."""
    if filename not in PIKE_ONLY_INGESTION:
        return INGESTION / filename
    return None


def resolve_pike_or_county_file(county: str, pike_filename: str, county_pattern: str) -> Path | None:
    """
    Pike-only files (ingestion/SalarySearch.csv etc.) return None for non-Pike.
    County-specific files use county_pattern.format(county=lower_name).
    """
    if is_pike(county):
        p = INGESTION / pike_filename
        return p if p.exists() else None
    alt = INGESTION / county_pattern.format(county=normalize_county(county).lower())
    return alt if alt.exists() else None


def anomalies_csv_for(county: str) -> Path | None:
    """County anomalies file only — never fall back to Pike anomalies.csv."""
    path = INGESTION / f"anomalies_{normalize_county(county).lower()}.csv"
    return path if path.exists() else None


def salary_inbox_candidates(county: str) -> list[Path]:
    """Salary file search paths — global SalarySearch.csv is Pike-only."""
    name = normalize_county(county)
    paths = [
        REPO_ROOT / "data" / "inbox" / f"{name}_SalarySearch.csv",
    ]
    if is_pike(county):
        paths.extend(
            [
                INGESTION / "SalarySearch.csv",
                REPO_ROOT / "data" / "inbox" / "SalarySearch.csv",
            ]
        )
    return paths
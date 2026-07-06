"""
Indiana Gateway public employee compensation — per-county loader.

Primary source: Gateway Employee Compensation report export (SalarySearch CSV format).
Cache: data/cache/salaries/salary_{gateway_code}_{year}.csv

Gateway report UI uses ReportViewer (ASP.NET); automated export is best-effort.
Drop exports in data/inbox/ as {County}_SalarySearch.csv or the zip bundle.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

from core.handoff import SalaryEntry, SourceRef
from tools.public_data_loaders import INGESTION, REPO_ROOT, _dept_readable, _money

SALARY_CACHE_DIR = REPO_ROOT / "data" / "cache" / "salaries"
REPORT_URL = (
    "https://gateway.ifionline.org/report_builder/Default3a.aspx"
    "?rptType=employComp&rpt=EmployComp&rptName=Employee+Compensation"
)
SALARY_SEARCH_URL = "https://gateway.ifionline.org/report_builder/Default2.aspx?rptType=employComp&rptVer=a"


def _salary_cache_path(gateway_code: int, year: int) -> Path:
    SALARY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return SALARY_CACHE_DIR / f"salary_{gateway_code}_{year}.csv"


def _candidate_paths(county_name: str, gateway_code: int, year: int) -> list[Path]:
    from tools.county_isolation import is_pike, normalize_county, salary_inbox_candidates

    name = normalize_county(county_name)
    paths: list[Path] = [
        _salary_cache_path(gateway_code, year),
        INGESTION / f"{name}_SalarySearch.csv",
        INGESTION / f"{name.lower()}_salary_{year}.csv",
    ]
    paths.extend(salary_inbox_candidates(name))
    if is_pike(name):
        paths.append(INGESTION / "SalarySearch.csv")
    return paths


def parse_salary_export(path: Path) -> list[dict]:
    """Parse Gateway SalarySearch / Employee Compensation CSV export."""
    if not path.exists():
        return []

    with path.open(encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        rows = list(reader)

    data_start = 0
    for i, row in enumerate(rows):
        if row and row[0] == "Textbox6":
            data_start = i + 1
            break
        if row and len(row) >= 6 and "compensation" in (row[0] or "").lower():
            data_start = i + 1
            break

    records: list[dict] = []
    for row in rows[data_start:]:
        if len(row) < 6:
            continue
        comp = _money(row[5]) if len(row) > 5 else None
        if comp is None or comp < 100:
            continue
        dept = row[2].strip() if len(row) > 2 else ""
        records.append(
            {
                "name": row[1].strip().strip('"') if len(row) > 1 else "",
                "department": dept,
                "department_readable": _dept_readable(dept),
                "job_title": row[3].strip() if len(row) > 3 else "",
                "city": row[4].strip() if len(row) > 4 else "",
                "compensation": comp,
            }
        )
    return records


def ensure_county_salary_file(
    county_name: str,
    gateway_code: int,
    year: int = 2025,
) -> tuple[Path | None, str]:
    """
    Resolve salary CSV for a county. Returns (path, status_message).
    Does not fail — missing salary is a data_gap, not a crash.
    """
    for path in _candidate_paths(county_name, gateway_code, year):
        if path.exists() and path.stat().st_size > 200:
            return path, f"salary cache hit: {path.name}"

    return None, (
        f"No salary export for {county_name} (gateway_code={gateway_code}). "
        f"Export from {SALARY_SEARCH_URL} → save as "
        f"data/cache/salaries/salary_{gateway_code}_{year}.csv or data/inbox/{county_name}_SalarySearch.csv"
    )


def load_county_salary_records(
    county_name: str,
    *,
    gateway_code: int,
    year: int = 2025,
) -> tuple[list[dict], list[SourceRef], str]:
    path, status = ensure_county_salary_file(county_name, gateway_code, year)
    if not path:
        return [], [], status

    records = parse_salary_export(path)
    sources = [
        SourceRef(
            kind="web" if "cache" in str(path) else "manual",
            url=SALARY_SEARCH_URL,
            note=f"Gateway employee compensation → {path.name} ({len(records)} records)",
        )
    ]
    return records, sources, status


def load_county_salaries(
    county_name: str,
    *,
    gateway_code: int,
    year: int = 2025,
    max_departments: int = 8,
) -> tuple[list[SalaryEntry], list[SourceRef], list[dict]]:
    """Aggregated SalaryEntry list + raw detail records for red-flag detectors."""
    records, sources, _ = load_county_salary_records(
        county_name, gateway_code=gateway_code, year=year
    )
    if not records:
        return [], [], []

    by_dept: dict[str, list[int]] = defaultdict(list)
    for rec in records:
        by_dept[rec["department_readable"]].append(rec["compensation"])

    salaries: list[SalaryEntry] = []
    for dept, amounts in sorted(by_dept.items(), key=lambda x: -sum(x[1]))[:max_departments]:
        salaries.append(
            SalaryEntry(
                department=dept,
                position="(aggregated roles)",
                employee_count=len(amounts),
                avg_salary=int(sum(amounts) / len(amounts)),
                min_salary=min(amounts),
                max_salary=max(amounts),
                year=year,
                notes=f"Gateway compensation export; {len(amounts)} records.",
            )
        )

    return salaries, sources, records
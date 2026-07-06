"""
Load real public data from ingestion/ caches and session downloads.

These are NOT seeds — they are exported from Indiana Gateway, DOR budget
certification, and salary transparency sources (see data/public_data_sources.yaml).
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

from core.handoff import BudgetData, SalaryEntry, SourceRef

REPO_ROOT = Path(__file__).resolve().parent.parent
INGESTION = REPO_ROOT / "ingestion"

DEPT_NAMES = {
    "0005": "Sheriff",
    "0061": "County Council",
    "0068": "Commissioners",
    "0380": "County Jail",
    "0506": "Solid Waste",
    "1219": "Park & Recreation",
    "0303": "E911",
    "0232": "Circuit Court",
    "Highway": "Highway",
    "EMS": "EMS",
}


def _dept_readable(dept: str) -> str:
    key = dept.split()[0] if dept else ""
    return DEPT_NAMES.get(key, dept)


def _money(s: str) -> int | None:
    if not s:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", str(s))
    if not cleaned:
        return None
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def load_pike_budgets_from_textmode(
    county_label: str = "Pike County, IN",
    fiscal_year: int = 2025,
) -> tuple[list[BudgetData], list[SourceRef]]:
    """Parse ingestion/pike_budget_textmode.csv into BudgetData entries."""
    path = INGESTION / "pike_budget_textmode.csv"
    if not path.exists():
        return [], []

    county_rows: dict[str, list[dict]] = defaultdict(list)
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("county") != county_label:
                continue
            if int(float(row.get("fiscal_year", 0))) != fiscal_year:
                continue
            dept = row.get("department", "")
            county_rows[dept].append(row)

    budgets: list[BudgetData] = []
    sources = [
        SourceRef(
            kind="manual",
            url="https://www.in.gov/dor/budget-and-claims/budget-orders/",
            note=f"DOR budget certification textmode → {path.name} (real public data)",
        )
    ]

    # County-level aggregate
    pike_dept = county_rows.get("PIKE COUNTY", [])
    if pike_dept:
        total = sum(float(r["amount"]) for r in pike_dept)
        major = {r["category"]: int(float(r["amount"])) for r in pike_dept}
        prev_path = INGESTION / "pike_county_totals_2022_2025.csv"
        prev_total = None
        if prev_path.exists():
            with prev_path.open(encoding="utf-8") as pf:
                for pr in csv.DictReader(pf):
                    if pr.get("department") == "PIKE COUNTY" and int(pr["fiscal_year"]) == fiscal_year - 1:
                        prev_total = int(float(pr["amount"]))
        deficit_note = ""
        if prev_total:
            delta = total - prev_total
            pct = delta / prev_total * 100
            deficit_note = f" YoY certified total change: {pct:+.1f}% (${delta:+,})."
        budgets.append(
            BudgetData(
                fiscal_year=fiscal_year,
                entity="Pike County",
                total_expenditures=int(total),
                major_funds=major,
                notes=(
                    f"From DOR budget certification textmode ({len(pike_dept)} fund lines). "
                    f"Certified total ${total:,.0f}.{deficit_note}"
                ),
                source=sources[0],
            )
        )

    # Winslow town
    winslow = county_rows.get("WINSLOW CIVIL TOWN", [])
    if winslow:
        total = sum(float(r["amount"]) for r in winslow)
        major = {r["category"]: int(float(r["amount"])) for r in winslow}
        budgets.append(
            BudgetData(
                fiscal_year=fiscal_year,
                entity="Winslow Town",
                total_expenditures=int(total),
                major_funds=major,
                notes=f"Winslow Civil Town certified funds from textmode ({len(winslow)} lines).",
                source=sources[0],
            )
        )

    # Petersburg (nearby reference)
    pete = county_rows.get("PETERSBURG CIVIL CITY", [])
    if pete:
        total = sum(float(r["amount"]) for r in pete)
        budgets.append(
            BudgetData(
                fiscal_year=fiscal_year,
                entity="Petersburg City",
                total_expenditures=int(total),
                notes="Petersburg Civil City certified budget (county seat comparison).",
                source=sources[0],
            )
        )

    return budgets, sources


def load_multi_year_budget_totals(
    county_label: str = "Pike County, IN",
    department: str | None = None,
    *,
    gateway_code: int | None = None,
) -> list[dict]:
    """
    Year-by-year certified totals from statewide Gateway cache (all 92 counties).
    Pike ingestion/pike_county_totals_2022_2025.csv is used ONLY when county is Pike.
    """
    from tools.county_isolation import is_pike, normalize_county

    short = normalize_county(county_label.replace(", IN", ""))
    try:
        from tools.indiana_county_budget import load_county_budget_totals_series

        series = load_county_budget_totals_series(short, gateway_code=gateway_code)
        if series:
            return series
    except Exception:
        pass

    if not is_pike(short):
        return []

    dept = department or f"{short.upper()} COUNTY"
    path = INGESTION / "pike_county_totals_2022_2025.csv"
    if not path.exists():
        return []

    label = f"{short} County, IN"
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("county") != label or row.get("department") != dept:
                continue
            rows.append({"year": int(row["fiscal_year"]), "amount": int(float(row["amount"]))})

    rows.sort(key=lambda x: x["year"])
    for i in range(1, len(rows)):
        prev = rows[i - 1]["amount"]
        if prev > 0:
            rows[i]["yoy_pct"] = round((rows[i]["amount"] - prev) / prev * 100, 1)
    return rows


def load_salary_detail_records_for_county(
    county: str = "Pike",
    *,
    gateway_code: int | None = None,
    year: int = 2025,
) -> list[dict]:
    """County-aware salary detail records (Gateway export cache or inbox).

    Never falls back to another county's export — missing cache returns [].
    """
    from tools.indiana_gateway_salary import load_county_salary_records

    if gateway_code is None:
        from tools.county_data_fetch import resolve_county

        meta = resolve_county(county) or {}
        gateway_code = meta.get("gateway_code")
    if not gateway_code:
        return []
    records, _, _ = load_county_salary_records(county, gateway_code=gateway_code, year=year)
    return records


def load_pike_budgets_multi_year(
    county_label: str = "Pike County, IN",
    years: list[int] | None = None,
) -> tuple[list[BudgetData], list[SourceRef]]:
    """BudgetData entries for each year in totals file (county-wide certified)."""
    series = load_multi_year_budget_totals(county_label=county_label)
    if years:
        series = [s for s in series if s["year"] in years]

    sources = [
        SourceRef(
            kind="manual",
            url="https://www.in.gov/dor/budget-and-claims/budget-orders/",
            note="DOR certified budget totals 2022-2025 → pike_county_totals_2022_2025.csv",
        )
    ]
    budgets: list[BudgetData] = []
    for item in series:
        note = f"Certified PIKE COUNTY total FY{item['year']}."
        if item.get("yoy_pct") is not None:
            note += f" YoY {item['yoy_pct']:+.1f}%."
        budgets.append(
            BudgetData(
                fiscal_year=item["year"],
                entity="Pike County (certified total)",
                total_expenditures=item["amount"],
                notes=note,
                source=sources[0],
            )
        )
    return budgets, sources


def load_salary_detail_records() -> list[dict]:
    """Pike-only: ingestion/SalarySearch.csv. Other counties must use load_salary_detail_records_for_county."""
    path = INGESTION / "SalarySearch.csv"
    if not path.exists():
        return []

    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    data_start = 0
    for i, row in enumerate(rows):
        if row and row[0] == "Textbox6":
            data_start = i + 1
            break

    records: list[dict] = []
    for row in rows[data_start:]:
        if len(row) < 6:
            continue
        comp = _money(row[5])
        if comp is None or comp < 100:
            continue
        dept = row[2].strip()
        records.append(
            {
                "name": row[1].strip().strip('"'),
                "department": dept,
                "department_readable": _dept_readable(dept),
                "job_title": row[3].strip(),
                "city": row[4].strip() if len(row) > 4 else "",
                "compensation": comp,
            }
        )
    return records


def load_pike_salaries_from_gateway_export(
    fiscal_year: int = 2025,
    max_departments: int = 8,
) -> tuple[list[SalaryEntry], list[SourceRef]]:
    """Parse ingestion/SalarySearch.csv (Gateway salary transparency export)."""
    path = INGESTION / "SalarySearch.csv"
    if not path.exists():
        return [], []

    sources = [
        SourceRef(
            kind="manual",
            url="https://gateway.ifionline.org/public/SESalarySearch.aspx",
            note=f"Indiana public employee compensation export → {path.name}",
        )
    ]

    by_dept: dict[str, list[int]] = defaultdict(list)
    with path.open(encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Data starts at row with Textbox6 header (0-indexed row 6 in file)
    data_start = 0
    for i, row in enumerate(rows):
        if row and row[0] == "Textbox6":
            data_start = i + 1
            break

    for row in rows[data_start:]:
        if len(row) < 6:
            continue
        dept = row[2].strip() if len(row) > 2 else ""
        title = row[3].strip() if len(row) > 3 else ""
        comp = _money(row[5]) if len(row) > 5 else None
        if not dept or comp is None or comp < 1000:
            continue
        dept_name = _dept_readable(dept)
        by_dept[dept_name].append(comp)

    salaries: list[SalaryEntry] = []
    for dept, amounts in sorted(by_dept.items(), key=lambda x: -sum(x[1]))[:max_departments]:
        if len(amounts) < 1:
            continue
        salaries.append(
            SalaryEntry(
                department=dept,
                position="(aggregated roles)",
                employee_count=len(amounts),
                avg_salary=int(sum(amounts) / len(amounts)),
                min_salary=min(amounts),
                max_salary=max(amounts),
                year=fiscal_year,
                notes=f"From Gateway salary search export; {len(amounts)} compensation records.",
            )
        )

    return salaries, sources


def load_budget_anomaly_excerpts(county: str = "Pike") -> tuple[list[str], list[SourceRef]]:
    """Pull anomaly script lines from anomalies_{county}.csv only (never Pike global for others)."""
    from tools.county_isolation import anomalies_csv_for, is_pike, normalize_county

    name = normalize_county(county)
    path = anomalies_csv_for(name)
    if not path and is_pike(name):
        path = INGESTION / "anomalies.csv"
    if not path or not path.exists():
        return [], []

    excerpts: list[str] = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if county.lower() not in row.get("county", "").lower():
                continue
            line = row.get("script_line") or row.get("note", "")
            if line:
                excerpts.append(line)

    sources = [
        SourceRef(
            kind="manual",
            note=f"DOGEGPT budget anomaly pipeline output → {path.name}",
        )
    ]
    return excerpts[:10], sources


def gateway_disbursement_stats(
    file_path: Path,
    county_name: str = "Pike",
) -> tuple[dict[str, float | int | str], list[str]]:
    """Summarize a Gateway disbursements file for a county (pipe-delimited)."""
    if not file_path.exists():
        return {}, []

    total_amount = 0.0
    vendors: dict[str, float] = defaultdict(float)
    lines = 0
    excerpts: list[str] = []

    with file_path.open(encoding="utf-8", errors="replace") as f:
        header = f.readline()
        cols = [c.strip().lower() for c in header.split("|")]
        county_idx = next(
            (i for i, c in enumerate(cols) if c in ("cnty_description", "county", "county_name")),
            next((i for i, c in enumerate(cols) if "cnty_description" in c), None),
        )
        unit_idx = next((i for i, c in enumerate(cols) if c == "unit_name"), None)
        fund_idx = next((i for i, c in enumerate(cols) if c == "fund_name"), None)
        amt_idx = next((i for i, c in enumerate(cols) if c == "amount" or c.endswith("amount")), None)

        for line in f:
            parts = line.split("|")
            if county_idx is None or len(parts) <= county_idx:
                continue
            if county_name.lower() not in parts[county_idx].lower():
                continue
            lines += 1
            if amt_idx is not None and len(parts) > amt_idx:
                try:
                    amt = float(parts[amt_idx].replace(",", "").strip() or 0)
                    total_amount += amt
                    label = ""
                    if fund_idx is not None and len(parts) > fund_idx:
                        label = parts[fund_idx].strip()
                    elif unit_idx is not None and len(parts) > unit_idx:
                        label = parts[unit_idx].strip()
                    if label:
                        vendors[label] += amt
                except ValueError:
                    pass

    top_funds = sorted(vendors.items(), key=lambda x: -x[1])[:5]
    for fund, a in top_funds:
        excerpts.append(f"Top disbursement fund in {county_name} County: {fund} (${a:,.0f})")

    stats = {
        "transaction_lines": lines,
        "total_disbursed": round(total_amount, 2),
        "unique_vendors": len(vendors),
        "county": county_name,
    }
    return stats, excerpts
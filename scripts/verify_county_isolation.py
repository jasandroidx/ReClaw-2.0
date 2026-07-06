#!/usr/bin/env python3
"""Assert Pike ingestion never bleeds into other counties."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.county_isolation import is_pike
from tools.public_data_loaders import (
    load_budget_anomaly_excerpts,
    load_multi_year_budget_totals,
    load_salary_detail_records_for_county,
)


def main() -> int:
    errors: list[str] = []

    # Spencer must not get Pike salaries
    spencer_sal = load_salary_detail_records_for_county("Spencer", gateway_code=74)
    pike_names = {r["name"] for r in load_salary_detail_records_for_county("Pike", gateway_code=63)}
    overlap = [r["name"] for r in spencer_sal if r["name"] in pike_names and "Wood" in r["name"]]
    if overlap and not any("Spencer" in str(r) for r in spencer_sal):
        errors.append(f"Spencer salary list may include Pike bleed: {overlap[:3]}")

    # Spencer budget trend must not use Pike totals file
    spencer_trend = load_multi_year_budget_totals(
        county_label="Spencer County, IN", gateway_code=74
    )
    pike_only_trend = load_multi_year_budget_totals(
        county_label="Pike County, IN", gateway_code=63
    )
    if spencer_trend and pike_only_trend and spencer_trend == pike_only_trend:
        errors.append("Spencer budget trend identical to Pike — isolation failure")

    # Spencer anomalies must not come from Pike-only anomalies.csv
    sp_ex, _ = load_budget_anomaly_excerpts("Spencer")
    for line in sp_ex:
        if "pike county" in line.lower() and "spencer" not in line.lower():
            errors.append(f"Spencer anomaly excerpt mentions Pike: {line[:80]}")

    # Pike still works
    if not is_pike("Pike"):
        errors.append("is_pike broken")
    pike_sal = load_salary_detail_records_for_county("Pike", gateway_code=63)
    if not pike_sal:
        errors.append("Pike salary cache empty (expected cached)")

    if errors:
        print("FAIL:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("OK: county isolation checks passed (Spencer ≠ Pike)")
    print(f"  Spencer salaries: {len(spencer_sal)} records")
    print(f"  Spencer budget years: {len(spencer_trend)}")
    print(f"  Spencer anomaly excerpts: {len(sp_ex)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
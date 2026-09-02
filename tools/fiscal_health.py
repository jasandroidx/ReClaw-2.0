"""
MSU-style local government fiscal stress ratios from Indiana Gateway budget file.

Uses certified budget fields (cash balance, operating balance, misc revenue, loans)
as proxies until full ACFR parsing lands.
"""

from __future__ import annotations

import json

from core.handoff import RedFlag
from tools.indiana_county_budget import load_county_budget_rows

SRC = "https://gateway.ifionline.org/public/download.aspx"

# MSU vulnerability framework — illustrative thresholds for rural IN counties
FUND_BALANCE_WARN = 0.10  # cash/operating balance < 10% of expenditures
FUND_BALANCE_CRIT = 0.05
DEBT_LOAD_WARN = 0.15  # outstanding temp loans / expenditures
INTERGOV_WARN = 0.35  # misc Form-2 revenue / total funds


def _f(row: dict, *keys: str) -> float:
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip():
            try:
                return float(str(v).replace(",", ""))
            except ValueError:
                continue
    return 0.0


def detect_fiscal_stress(
    county: str,
    *,
    gateway_code: int | None = None,
    year: int = 2025,
) -> list[RedFlag]:
    """
    Aggregate county-unit budget rows into fiscal health ratios.
    Flags thin reserves or heavy reliance on non-tax revenue.
    """
    name = county.replace(" County", "").strip()
    rows = load_county_budget_rows(name, gateway_code=gateway_code, year=year)
    rows = [r for r in rows if (r.get("unit_name") or "").upper() == f"{name.upper()} COUNTY"]
    if not rows:
        return []

    expenditures = sum(_f(r, "Total budget estimate_adopted", "Necessary expenditures_adopted") for r in rows)
    cash_balance = sum(_f(r, "Actual cash balance_adopted") for r in rows)
    operating_balance = sum(_f(r, "Operating balance_adopted") for r in rows)
    misc_rev = sum(
        _f(r, "Misc revenue from Form 2 ColA_adopted")
        + _f(r, "Misc revenue from Form 2 ColB_adopted")
        for r in rows
    )
    total_funds = sum(_f(r, "Total funds_adopted") for r in rows)
    temp_loans = sum(
        _f(r, "Outstanding temp loans to be paid_adopted")
        + _f(r, "Outstanding temp loans not repaid_adopted")
        for r in rows
    )

    if expenditures <= 0:
        return []

    flags: list[RedFlag] = []
    reserve = max(cash_balance, operating_balance)
    reserve_ratio = reserve / expenditures

    if reserve_ratio < FUND_BALANCE_CRIT:
        flags.append(
            RedFlag(
                severity="high",
                category="budget_spike",
                description=(
                    f"{name} County FY{year}: operating/cash reserves only "
                    f"{reserve_ratio*100:.1f}% of certified expenditures "
                    f"(${reserve:,.0f} vs ${expenditures:,.0f}) — thin cushion"
                ),
                evidence=json.dumps(
                    {
                        "ratio": round(reserve_ratio, 4),
                        "reserve": reserve,
                        "expenditures": expenditures,
                        "year": year,
                        "method": "msu_fund_balance_proxy",
                        "source": "gateway_budget",
                    }
                ),
                recommended_action="Compare to prior-year ACFR fund balance note; ask council about reserve policy.",
            )
        )
    elif reserve_ratio < FUND_BALANCE_WARN:
        flags.append(
            RedFlag(
                severity="medium",
                category="budget_spike",
                description=(
                    f"{name} County FY{year}: reserves at {reserve_ratio*100:.1f}% of "
                    f"expenditures (${reserve:,.0f}) — below typical 10%+ benchmark"
                ),
                evidence=json.dumps(
                    {
                        "ratio": round(reserve_ratio, 4),
                        "reserve": reserve,
                        "expenditures": expenditures,
                        "year": year,
                        "method": "msu_fund_balance_proxy",
                        "source": "gateway_budget",
                    }
                ),
                recommended_action="Monitor in next budget hearing; cite Gateway certified estimate.",
            )
        )

    if expenditures > 0 and temp_loans / expenditures >= DEBT_LOAD_WARN:
        debt_ratio = temp_loans / expenditures
        flags.append(
            RedFlag(
                severity="medium",
                category="composition_break",
                description=(
                    f"{name} County FY{year}: outstanding temporary loans "
                    f"${temp_loans:,.0f} = {debt_ratio*100:.1f}% of expenditures"
                ),
                evidence=json.dumps(
                    {
                        "temp_loans": temp_loans,
                        "expenditures": expenditures,
                        "ratio": round(debt_ratio, 4),
                        "year": year,
                        "method": "msu_debt_service_proxy",
                        "source": "gateway_budget",
                    }
                ),
                recommended_action="Cross-check debt schedule in SBOA audit PDF.",
            )
        )

    if total_funds > 0 and misc_rev / total_funds >= INTERGOV_WARN:
        ig_ratio = misc_rev / total_funds
        flags.append(
            RedFlag(
                severity="medium",
                category="federal_spending_spike",
                description=(
                    f"{name} County FY{year}: misc / intergovernmental-style revenue "
                    f"${misc_rev:,.0f} is {ig_ratio*100:.1f}% of total budgeted funds"
                ),
                evidence=json.dumps(
                    {
                        "misc_revenue": misc_rev,
                        "total_funds": total_funds,
                        "ratio": round(ig_ratio, 4),
                        "year": year,
                        "method": "msu_intergov_dependence_proxy",
                        "source": "gateway_budget",
                    }
                ),
                recommended_action="Identify grant pass-through vs own-source revenue in ACFR.",
            )
        )

    return flags
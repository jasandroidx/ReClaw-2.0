"""
Taxpayer-focused red flag detection — multi-year budgets, salaries, disbursements.

Surfaces what rural taxpayers would want to know (or be furious about) for
faceless watchdog / salary shock videos. Truth + provenance only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.handoff import Insight, RedFlag, ResearchPackage
from tools.public_data_loaders import (
    INGESTION,
    REPO_ROOT,
    gateway_disbursement_stats,
    load_multi_year_budget_totals,
    load_salary_detail_records,
)

# Rural IN county — rough thresholds for "would taxpayers care?"
COUNTY_POP_APPROX = 12_200
SALARY_SHOCK_FULL_TIME = 75_000
SALARY_SHOCK_ANY = 90_000
BUDGET_YOY_WARN_PCT = 8.0
BUDGET_YOY_FURY_PCT = 12.0
MULTIYEAR_WARN_PCT = 18.0  # 4-year cumulative


@dataclass
class TaxpayerScanResult:
    red_flags: list[RedFlag]
    insights: list[Insight]
    content_angles: list[str]
    budget_implications: list[str]
    video_titles: list[str]


def _gateway_cache_dir() -> Path:
    return REPO_ROOT / "data" / "cache"


def detect_budget_trend_flags(county: str = "Pike") -> tuple[list[RedFlag], list[Insight], list[str]]:
    """Multi-year certified budget totals (2022–2025)."""
    flags: list[RedFlag] = []
    insights: list[Insight] = []
    angles: list[str] = []

    series = load_multi_year_budget_totals(county_label=f"{county} County, IN")
    if len(series) < 2:
        return flags, insights, angles

    first, last = series[0], series[-1]
    span_years = last["year"] - first["year"]
    if span_years <= 0 or first["amount"] <= 0:
        return flags, insights, angles

    cumulative_pct = (last["amount"] - first["amount"]) / first["amount"] * 100
    annualized = cumulative_pct / span_years

    insights.append(
        Insight(
            category="budget",
            title=f"{county} certified budget grew {cumulative_pct:+.1f}% in {span_years} years",
            detail=(
                f"FY{first['year']} ${first['amount']:,} → FY{last['year']} ${last['amount']:,}. "
                f"~{annualized:+.1f}% per year average with flat/rural population — taxpayers feel this at levy time."
            ),
            supporting_numbers=[
                f"{y['year']}: ${y['amount']:,}" + (f" ({y['yoy_pct']:+.1f}% YoY)" if y.get("yoy_pct") is not None else "")
                for y in series
            ],
            suggested_angle=(
                f"{county} County raised certified spending {cumulative_pct:.0f}% since {first['year']} — "
                "where did YOUR property tax money go?"
            ),
        )
    )
    angles.append(insights[-1].suggested_angle or "")

    if cumulative_pct >= MULTIYEAR_WARN_PCT:
        flags.append(
            RedFlag(
                severity="high" if cumulative_pct >= 25 else "medium",
                category="budget_growth",
                description=(
                    f"Certified county budget up {cumulative_pct:.1f}% over {span_years} years "
                    f"(${first['amount']:,} → ${last['amount']:,}) while population is ~{COUNTY_POP_APPROX:,}."
                ),
                evidence="ingestion/pike_county_totals_2022_2025.csv (DOR certified totals)",
                recommended_action="Compare to property tax bills and levy hearings; strong watchdog video hook.",
            )
        )

    for y in series:
        yoy = y.get("yoy_pct")
        if yoy is None:
            continue
        if yoy >= BUDGET_YOY_FURY_PCT:
            flags.append(
                RedFlag(
                    severity="high",
                    category="budget_spike",
                    description=f"FY{y['year']} certified budget jumped {yoy:+.1f}% in one year (${y['amount']:,}).",
                    evidence="Year-over-year DOR certified totals",
                    recommended_action="Pull that year's budget order PDF and council votes.",
                )
            )
            angles.append(f"Why {county} County's {y['year']} budget spiked {yoy:.0f}% in a single year")
        elif yoy >= BUDGET_YOY_WARN_PCT:
            flags.append(
                RedFlag(
                    severity="medium",
                    category="budget_spike",
                    description=f"FY{y['year']} budget rose {yoy:+.1f}% YoY — above typical inflation for a rural county.",
                    evidence="DOR certified totals",
                    recommended_action="Cross-check road bonds and reassessment line items.",
                )
            )

    return flags, insights, angles


def detect_fund_imbalance_flags(research: ResearchPackage) -> tuple[list[RedFlag], list[str]]:
    """Current-year fund mix oddities from textmode certification."""
    flags: list[RedFlag] = []
    angles: list[str] = []

    county_budget = next((b for b in research.budgets if b.entity == "Pike County"), None)
    if not county_budget or not county_budget.major_funds:
        return flags, angles

    funds = county_budget.major_funds
    highway = funds.get("HIGHWAY", 0) + funds.get("LOCAL ROAD & STREET", 0)
    parks = funds.get("PARK & RECREATION", 0)
    reassess = funds.get("2015 REASSESSMENT", 0) or funds.get("REASSESSMENT", 0)
    total = county_budget.total_expenditures or sum(funds.values())

    if highway and parks and parks / highway > 0.25:
        flags.append(
            RedFlag(
                severity="medium",
                category="spending_priority",
                description=(
                    f"Parks & Recreation certified at ${parks:,} is "
                    f"{parks/highway*100:.0f}% of highway/road spend (${highway:,}) — unusual for a bridge-heavy rural county."
                ),
                evidence="ingestion/pike_budget_textmode.csv FY2025",
                recommended_action="Ask whether parks spending matches voter priorities vs road decay.",
            )
        )
        angles.append(f"Pike County spends ${parks:,} on parks vs ${highway:,} on roads — taxpayers decide if that's fair")

    if reassess and total and reassess / total > 0.02:
        flags.append(
            RedFlag(
                severity="medium",
                category="reassessment",
                description=(
                    f"Reassessment fund line ${reassess:,} in certified budget — "
                    "often precedes property tax bill changes taxpayers didn't expect."
                ),
                evidence="DOR textmode budget certification",
                recommended_action="Tie to homeowner tax shock stories; cite certified rate in CSV.",
            )
        )
        angles.append("Pike County's reassessment line item — what it means for your property tax bill")

    return flags, angles


def detect_salary_flags(county: str = "Pike", year: int = 2025) -> TaxpayerScanResult:
    """Individual salary records — shock list, double-dips, part-time anomalies."""
    flags: list[RedFlag] = []
    insights: list[Insight] = []
    angles: list[str] = []
    titles: list[str] = []
    implications: list[str] = []

    records = load_salary_detail_records()
    if not records:
        return TaxpayerScanResult(flags, insights, angles, implications, titles)

    # Top earners (public record)
    top = sorted(records, key=lambda r: r["compensation"], reverse=True)[:15]
    for i, rec in enumerate(top[:8]):
        comp = rec["compensation"]
        name = rec["name"]
        title = rec["job_title"]
        dept = rec["department_readable"]

        if comp >= SALARY_SHOCK_ANY:
            flags.append(
                RedFlag(
                    severity="high",
                    category="salary_shock",
                    description=(
                        f"{name} — {title} ({dept}): ${comp:,} in {year} public compensation. "
                        f"In a county of ~{COUNTY_POP_APPROX:,}, that's a taxpayer talking-point."
                    ),
                    evidence="gateway.ifionline.org Salary Search export → ingestion/SalarySearch.csv",
                    recommended_action="Verify full-time vs part-time; compare to IN rural averages for role.",
                )
            )
            if i < 5:
                titles.append(f"{county} County pays {title} ${comp:,} — here's what taxpayers should know")
                angles.append(f"#{i+1} highest paid: {name} (${comp:,}) — {title}")

        elif comp >= SALARY_SHOCK_FULL_TIME and "deputy" in title.lower() or "sheriff" in title.lower():
            flags.append(
                RedFlag(
                    severity="medium",
                    category="law_enforcement_pay",
                    description=f"{name} ({title}): ${comp:,} — high for rural public safety payroll.",
                    evidence="Public salary transparency export",
                    recommended_action="Compare to adjacent counties via Gateway search.",
                )
            )

    # Double-dip: same name, multiple rows summing high
    by_name: dict[str, list[dict]] = {}
    for rec in records:
        by_name.setdefault(rec["name"], []).append(rec)

    for name, rows in by_name.items():
        if len(rows) < 2:
            continue
        total = sum(r["compensation"] for r in rows)
        if total >= 50_000 and len(rows) >= 2:
            roles = ", ".join(f"{r['job_title']} (${r['compensation']:,})" for r in rows[:3])
            flags.append(
                RedFlag(
                    severity="medium" if total < 80_000 else "high",
                    category="double_dip",
                    description=(
                        f"{name} appears on {len(rows)} compensation lines totaling ${total:,}: {roles}."
                    ),
                    evidence="Salary Search CSV — multiple rows same employee",
                    recommended_action="Classic taxpayer fury angle: one person, multiple public paychecks.",
                )
            )
            angles.append(f"One name, multiple checks: {name} collected ${total:,} from Pike County taxpayers")

    # Low vs high contrast (video gold)
    lifeguards = [r for r in records if "lifeguard" in r["job_title"].lower()]
    directors = [r for r in records if "director" in r["job_title"].lower() or "coordinator" in r["job_title"].lower()]
    if lifeguards and directors:
        lg_avg = sum(r["compensation"] for r in lifeguards) / len(lifeguards)
        dir_max = max(directors, key=lambda r: r["compensation"])
        insights.append(
            Insight(
                category="economy",
                title="Pay gap: seasonal lifeguards vs department directors",
                detail=(
                    f"Lifeguard avg ~${lg_avg:,.0f} vs {dir_max['job_title']} at ${dir_max['compensation']:,} "
                    f"({dir_max['name']}). Taxpayers love this contrast for Shorts."
                ),
                supporting_numbers=[f"Lifeguards: {len(lifeguards)} records", f"Top director: ${dir_max['compensation']:,}"],
                suggested_angle="What Pike County pays a lifeguard vs what it pays the EMS director",
            )
        )
        angles.append(insights[-1].suggested_angle or "")

    # Council / commissioner — part-time politics pay
    for rec in records:
        if any(k in rec["job_title"].lower() for k in ("council", "commissioner", "councilman")):
            if rec["compensation"] > 500:
                flags.append(
                    RedFlag(
                        severity="low",
                        category="elected_pay",
                        description=(
                            f"Elected/part-time role paid ${rec['compensation']:,}: "
                            f"{rec['name']} — {rec['job_title']}."
                        ),
                        evidence="Public compensation report",
                        recommended_action="Small dollar but high outrage-per-dollar for local politics content.",
                    )
                )

    implications.append(
        f"Top public paycheck in sample: ${top[0]['compensation']:,} ({top[0]['job_title']}). "
        "Salary transparency is pre-built Shorts content."
    )

    return TaxpayerScanResult(flags, insights, angles, implications, titles)


def detect_gateway_yoy_flags(
    county: str = "Pike",
    years: list[int] | None = None,
    cache_dir: Path | None = None,
) -> tuple[list[RedFlag], list[str]]:
    """Compare Gateway disbursement totals across cached years."""
    flags: list[RedFlag] = []
    angles: list[str] = []
    years = years or [2022, 2023, 2024, 2025]
    cache = cache_dir or _gateway_cache_dir()

    totals: list[tuple[int, float]] = []
    for year in sorted(years):
        path = cache / f"gateway_disbursements_{year}.txt"
        if not path.exists():
            continue
        stats, _ = gateway_disbursement_stats(path, county_name=county)
        if stats.get("total_disbursed"):
            totals.append((year, float(stats["total_disbursed"])))

    if len(totals) < 2:
        return flags, angles

    for i in range(1, len(totals)):
        y0, a0 = totals[i - 1]
        y1, a1 = totals[i]
        if a0 <= 0:
            continue
        pct = (a1 - a0) / a0 * 100
        if abs(pct) >= 15:
            flags.append(
                RedFlag(
                    severity="high" if abs(pct) >= 25 else "medium",
                    category="disbursement_swing",
                    description=(
                        f"Total Gateway disbursements {y0}→{y1}: {pct:+.1f}% "
                        f"(${a0:,.0f} → ${a1:,.0f}). Taxpayers fund every line."
                    ),
                    evidence=f"gateway.ifionline.org disbursements {y0} vs {y1}",
                    recommended_action="Drill into fund_name spikes (Education, Settlement, General).",
                )
            )
            angles.append(f"Pike County public spending swung {pct:+.0f}% between {y0} and {y1}")

    return flags, angles


def scan_taxpayer_red_flags(
    research: ResearchPackage,
    cache_dir: Path | None = None,
) -> TaxpayerScanResult:
    """Full taxpayer scan — budgets, salaries, funds, gateway YoY."""
    county = research.county
    all_flags: list[RedFlag] = []
    all_insights: list[Insight] = []
    all_angles: list[str] = []
    all_implications: list[str] = []
    all_titles: list[str] = []

    bf, bi, ba = detect_budget_trend_flags(county)
    all_flags.extend(bf)
    all_insights.extend(bi)
    all_angles.extend(ba)

    ff, fa = detect_fund_imbalance_flags(research)
    all_flags.extend(ff)
    all_angles.extend(fa)

    salary_result = detect_salary_flags(county)
    all_flags.extend(salary_result.red_flags)
    all_insights.extend(salary_result.insights)
    all_angles.extend(salary_result.content_angles)
    all_implications.extend(salary_result.budget_implications)
    all_titles.extend(salary_result.video_titles)

    gf, ga = detect_gateway_yoy_flags(county, cache_dir=cache_dir)
    all_flags.extend(gf)
    all_angles.extend(ga)

    # Dedupe angles
    seen: set[str] = set()
    unique_angles = []
    for a in all_angles:
        if a and a not in seen:
            seen.add(a)
            unique_angles.append(a)

    return TaxpayerScanResult(
        red_flags=all_flags,
        insights=all_insights,
        content_angles=unique_angles,
        budget_implications=all_implications,
        video_titles=all_titles,
    )
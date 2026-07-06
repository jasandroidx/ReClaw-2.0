"""
Analyst / Red Flag Agent — ReClaw 2.0

Mission: Convert raw research into rural-practical insights, budget implications,
and clear red flags. Output ready-to-use content angles for the faceless channel.

Style (from OpenClaw Orange Paper / rural data ethos):
- Brutally direct. No hype.
- Numbers first, then interpretation.
- Red flags are the product — they drive both caution stories and "hidden opportunity" angles.
- Every insight should suggest a concrete video angle or decision.

Current implementation: deterministic heuristics + rules.
Future: when settings.enable_llm_analysis, call local model on the research JSON for deeper narrative.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.config import get_settings
from core.handoff import (
    AnalysisPackage,
    Insight,
    RedFlag,
    ResearchPackage,
)
from core.security import SecurityManager
from core.session import Session
from tools.public_data_loaders import REPO_ROOT, load_multi_year_budget_totals, load_salary_detail_records
from tools.red_flag_engine import scan_all_red_flags
from tools.taxpayer_red_flags import scan_taxpayer_red_flags


class AnalystAgent:
    """
    Analyst / Red Flag Agent.

    OpenClaw patterns:
    - Loads agents/analyst/SOUL.md via session
    - Low-privilege by default (heuristic only)
    - Writes handoff to session for isolation + audit
    """

    SOUL_PATH = Path(__file__).parent / "analyst" / "SOUL.md"

    def __init__(self, settings: Any | None = None, session: Session | None = None):
        self.settings = settings or get_settings()
        self.session = session
        self.security: SecurityManager | None = None
        if self.session:
            self.security = SecurityManager(self.session.base_dir, self.session.session_id)
            soul_text = self.session.load_soul("analyst", self.SOUL_PATH)
            self.session.log(f"Analyst SOUL loaded (len={len(soul_text)} chars)")


    def run(self, research: ResearchPackage) -> AnalysisPackage:
        if self.session:
            self.session.log(f"Analyst starting on research {research.id}")
            # Record that we are using the low-risk capability
            if self.security:
                self.security.record_action("heuristic_analysis", {"research_id": research.id, "county": research.county})

        insights: list[Insight] = []
        red_flags: list[RedFlag] = []
        budget_implications: list[str] = []
        content_angles: list[str] = []

        county = research.county
        area = research.primary_area

        # === Taxpayer watchdog scan (multi-year budgets, salaries, disbursements) ===
        cache_dir = REPO_ROOT / "data" / "cache"
        if self.session:
            sess_cache = self.session.base_dir / "sources"
            if sess_cache.exists():
                cache_dir = sess_cache.parent  # prefer session-adjacent cache
        engine = scan_all_red_flags(research, cache_dir=REPO_ROOT / "data" / "cache")
        red_flags.extend(engine.red_flags)
        insights.extend(engine.insights)
        content_angles.extend(engine.content_angles)
        budget_implications.extend(engine.budget_implications)
        video_titles: list[str] = list(engine.video_titles)

        # === Supplemental excerpts not already captured by red_flag_engine ===
        known = {f.description[:80] for f in red_flags}
        for excerpt in research.raw_excerpts[:8]:
            if excerpt[:80] in known:
                continue
            lower = excerpt.lower()
            severity = "medium"
            category = "budget_anomaly"
            if "ecod" in lower or "isolationforest" in lower or "flagged" in lower:
                severity = "high"
                category = "statistical_anomaly"
            elif "vendor" in lower or "disbursement" in lower:
                category = "procurement"
            red_flags.append(
                RedFlag(
                    severity=severity,
                    category=category,
                    description=excerpt[:500],
                    evidence="Indiana Gateway / DOGEGPT pipeline (see ResearchPackage.sources)",
                    recommended_action="Pull supporting lines from gateway disbursements or budget CSV for video script.",
                )
            )
            content_angles.append(excerpt[:120])

        # === Budget analysis ===
        for b in research.budgets:
            highway_spend = b.major_funds.get("HIGHWAY", 0) or b.major_funds.get("LOCAL ROAD & STREET", 0)
            if highway_spend > 500_000:
                insights.append(
                    Insight(
                        category="infrastructure",
                        title=f"{b.entity} certified highway/road funds: ${highway_spend:,}",
                        detail="From DOR budget certification (real public data). Road pressure is the dominant rural budget story.",
                        supporting_numbers=[f"Highway/road certified: ${highway_spend:,}"],
                        suggested_angle=f"Where {b.entity}'s road money actually goes — certified budget breakdown",
                    )
                )

            if b.surplus_deficit is not None and b.surplus_deficit < 0:
                deficit_pct = abs(b.surplus_deficit) / max(b.total_expenditures or 1, 1) * 100
                red_flags.append(
                    RedFlag(
                        severity="medium" if deficit_pct < 8 else "high",
                        category="budget_deficit",
                        description=f"{b.entity} FY{b.fiscal_year} running ${abs(b.surplus_deficit):,} deficit ({deficit_pct:.1f}% of spend).",
                        evidence=f"Revenue ${b.total_revenue:,} vs Expenditures ${b.total_expenditures:,}",
                        recommended_action="Watch next levy hearing and road project bids. Content angle: 'Why your rural county is quietly going broke on bridges'.",
                    )
                )
                budget_implications.append(
                    f"{b.entity} will likely raise property taxes or cut maintenance in 2026 to close the gap."
                )

            if b.expenditure_categories.get("Highways/Roads", 0) > 800_000:
                insights.append(
                    Insight(
                        category="infrastructure",
                        title=f"{b.entity} spends heavily on roads — classic rural pressure point",
                        detail=f"Road & bridge category is one of the largest line items. In low-tax-base counties this is often the first thing to show visible decay.",
                        supporting_numbers=[f"${b.expenditure_categories.get('Highways/Roads', 0):,} on highways/roads"],
                        suggested_angle="Show before/after photos of county roads + explain where the money actually goes.",
                    )
                )

        # === Property market signals ===
        cheap_props = [p for p in research.property_records if p.assessed_value and p.assessed_value < 35000]
        if cheap_props:
            insights.append(
                Insight(
                    category="property",
                    title=f"{len(cheap_props)} parcels under $35k assessed in {area} area",
                    detail="Extremely low entry prices. Good for 'can you actually live on this' stories and land-banking angles. Also flags potential maintenance nightmares or title issues.",
                    supporting_numbers=[f"Lowest: ${min(p.assessed_value for p in cheap_props):,}", f"Median in sample: ${research.median_assessed or 0:,}"],
                    suggested_angle="The $25k house in rural Indiana — what's the real monthly cost?",
                )
            )
            content_angles.append(
                f"Top {min(5, len(cheap_props))} cheapest habitable properties in {county} County right now (and what they actually need)"
            )

        large_ag = [p for p in research.property_records if p.land_acres and p.land_acres > 20 and p.assessed_value and p.assessed_value < 150000]
        if large_ag:
            insights.append(
                Insight(
                    category="opportunity",
                    title="Large acreage still trading under $150k — watch for consolidation or outside money",
                    detail="47-acre example at ~$124k assessed is cheap by almost any national metric. Either the land has serious limitations or the local market hasn't caught up to remote buyer interest.",
                    supporting_numbers=[f"{p.land_acres} acres @ ${p.assessed_value:,}" for p in large_ag[:2]],
                    suggested_angle="Why 40+ acres in southern Indiana is still under $130k (and whether you want it)",
                )
            )

        # === Salary / labor reality ===
        low_pay = [s for s in research.salaries if s.avg_salary and s.avg_salary < 45000]
        if low_pay:
            insights.append(
                Insight(
                    category="economy",
                    title="Public sector pay remains very low vs national rural averages",
                    detail="Deputy and road crew roles in the low $40ks. This is both a 'people can't afford to live here on these wages' story and a 'why recruitment is impossible' story.",
                    supporting_numbers=[f"{s.position}: ~${s.avg_salary:,}" for s in low_pay],
                    suggested_angle="What a $47k sheriff deputy job actually buys you in Pike County 2026",
                )
            )

        # === Red flags from data patterns ===
        if research.median_assessed and research.median_assessed < 40000:
            red_flags.append(
                RedFlag(
                    severity="medium",
                    category="depressed_values",
                    description=f"Median assessed value in sample is only ${research.median_assessed:,}. Signals either very old housing stock, lack of economic activity, or both.",
                    evidence="Direct from property roll sample",
                    recommended_action="Cross-reference with building permits and demolition orders. Good 'dying small town' or 'quiet revival' bifurcation story.",
                )
            )

        # Hard deficit + high road spend combo
        has_deficit = any((b.surplus_deficit or 0) < 0 for b in research.budgets)
        high_road = any(b.expenditure_categories.get("Highways/Roads", 0) > 700_000 for b in research.budgets)
        if has_deficit and high_road:
            red_flags.append(
                RedFlag(
                    severity="high",
                    category="infrastructure_funding_gap",
                    description="Deficit + heavy road spend = classic rural trap. They are already underwater and the biggest expense category is non-optional.",
                    evidence="Budget + expenditure category cross-check",
                    recommended_action="Track the next cumulative bridge fund levy attempt. This is often where small counties quietly add 10-15% to tax bills.",
                )
            )

        trend = load_multi_year_budget_totals()
        if trend and len(trend) >= 2:
            y0, y1 = trend[0], trend[-1]
            if y0["amount"] > 0:
                cum = (y1["amount"] - y0["amount"]) / y0["amount"] * 100
                budget_implications.append(
                    f"Certified spending {y0['year']}→{y1['year']}: {cum:+.1f}% — taxpayers should compare to their property tax bills."
                )

        # Salary shock titles for Shorts
        salary_records = load_salary_detail_records()
        if salary_records:
            top = sorted(salary_records, key=lambda r: r["compensation"], reverse=True)[:5]
            for rec in top:
                video_titles.append(
                    f"Taxpayers paid {rec['name']} ${rec['compensation']:,} as {rec['job_title']} in {county} County"
                )

        content_angles.extend(video_titles[:6])

        if not content_angles:
            content_angles = [
                f"How {county} County's budget grew since 2022 — the numbers no one reads",
                f"{county} County salary transparency: who got paid the most with your tax dollars",
            ]

        high_sev = sum(1 for f in red_flags if f.severity in ("high", "critical"))
        overall_risk = min(10.0, 2.0 + high_sev * 2.2 + len(red_flags) * 0.6 + (1.0 if has_deficit else 0))

        summary = (
            f"{county} / {area}: {len(red_flags)} taxpayer red flags ({high_sev} high/critical), "
            f"{len(insights)} insights. Multi-year budget + public salary data wired for watchdog/Shorts content."
        )

        pkg = AnalysisPackage(
            research_id=research.id,
            county=county,
            primary_area=area,
            insights=insights,
            red_flags=red_flags,
            budget_implications=budget_implications,
            content_angles=content_angles,
            overall_risk_score=round(overall_risk, 1),
            summary=summary,
        )
        if self.session:
            self.session.write_handoff("analyst", pkg)
            self.session.log(f"Analyst complete. risk={pkg.overall_risk_score} flags={len(red_flags)}")
        return pkg

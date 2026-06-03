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

        # === Budget analysis ===
        for b in research.budgets:
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

        # Content angles (always produce some)
        if not content_angles:
            content_angles = [
                f"How {county} County's 2025 budget actually affects Winslow residents (the numbers no one reads)",
                "Rural Indiana property under $50k — the good, the bad, and the foundation issues",
                f"Why Pike County road crews make ${research.salaries[0].avg_salary if research.salaries else 42}k and what that means for your taxes",
            ]

        overall_risk = min(10.0, 2.0 + len(red_flags) * 1.8 + (1.0 if has_deficit else 0))

        summary = (
            f"{county} / {area} shows the typical rural squeeze: low asset values, structural budget pressure on infrastructure, "
            f"and wages that make it hard for working families to stay. {len(red_flags)} red flags and {len(insights)} insights extracted. "
            "Strong material for both cautionary and 'last cheap land' style faceless content."
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

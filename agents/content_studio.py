"""
Content Studio Agent — ReClaw 2.0

Turns AnalysisPackage red flags (and optional CompliancePackage) into
faceless Shorts/TikTok scripts with provenance. Prunes low-engagement angles.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.config import get_settings
from core.handoff import (
    AnalysisPackage,
    CompliancePackage,
    ContentStudioOutput,
    RedFlag,
    ResearchPackage,
    ShortScript,
)
from core.security import SecurityManager
from core.session import Session

SEVERITY_SCORE = {"critical": 0.95, "high": 0.88, "medium": 0.72, "low": 0.55}
CATEGORY_BOOST = {
    "salary_shock": 0.08,
    "double_dip": 0.07,
    "budget_spike": 0.06,
    "budget_growth": 0.05,
    "disbursement_swing": 0.06,
    "spending_priority": 0.05,
    "law_enforcement_pay": 0.04,
    "elected_pay": 0.05,
    "reassessment": 0.04,
}
MIN_ENGAGEMENT = 0.7
MAX_SCRIPTS = 3

TITLE_TEMPLATES: dict[str, str] = {
    "salary_shock": "{county} County paid {amount} — taxpayers need to see this",
    "double_dip": "Same name, two paychecks in {county} County public records",
    "budget_spike": "{county} budget line item spiked — the receipt is public",
    "budget_growth": "{county} spending grew since 2022 — where did your taxes go?",
    "disbursement_swing": "{county} County disbursements swung year over year",
    "spending_priority": "{county} spent more on parks than roads — public data",
    "law_enforcement_pay": "What {county} pays law enforcement (public salary search)",
    "elected_pay": "Elected officials' pay in {county} County — public record",
    "reassessment": "Your {county} property tax bill may jump — reassessment line item",
}

HOOK_TEMPLATES: dict[str, str] = {
    "salary_shock": "If you pay taxes in {county} County, you paid for this paycheck.",
    "double_dip": "One person. Two public paychecks. Same county. Public record.",
    "budget_spike": "County budget shocker — one line item just spiked, and almost nobody noticed.",
    "budget_growth": "Your county's certified spending climbed for years. The numbers are public.",
    "disbursement_swing": "Where did the money go? Gateway disbursements show a swing worth watching.",
    "spending_priority": "Roads or parks — see what your county prioritized with your tax dollars.",
    "default": "If you live in {county} County, this came from public records — not rumors.",
}


def _first_dollar_amount(text: str) -> str | None:
    match = re.search(r"\$[\d,]+(?:\.\d{2})?", text)
    return match.group(0) if match else None


def _engagement_score(flag: RedFlag) -> float:
    base = SEVERITY_SCORE.get(flag.severity, 0.6)
    boost = CATEGORY_BOOST.get(flag.category, 0.0)
    if _first_dollar_amount(flag.evidence) or _first_dollar_amount(flag.description):
        boost += 0.03
    return min(1.0, base + boost)


def _dedupe_flags(flags: list[RedFlag]) -> list[RedFlag]:
    seen: set[str] = set()
    out: list[RedFlag] = []
    for flag in flags:
        key = f"{flag.category}:{flag.description[:80]}"
        if key in seen:
            continue
        seen.add(key)
        out.append(flag)
    return out


def _rank_flags(flags: list[RedFlag]) -> list[tuple[RedFlag, float]]:
    ranked = [(f, _engagement_score(f)) for f in flags]
    ranked.sort(key=lambda x: (-x[1], {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x[0].severity, 9)))
    return ranked


def _title_for_flag(flag: RedFlag, county: str) -> str:
    template = TITLE_TEMPLATES.get(flag.category, "{county} County: {category} red flag")
    amount = _first_dollar_amount(flag.evidence) or _first_dollar_amount(flag.description) or ""
    return template.format(
        county=county,
        category=flag.category.replace("_", " "),
        amount=amount,
    ).strip(" —")


def _hook_for_flag(flag: RedFlag, county: str) -> str:
    template = HOOK_TEMPLATES.get(flag.category, HOOK_TEMPLATES["default"])
    return template.format(county=county)


def _script_body(flag: RedFlag, county: str, hook: str) -> str:
    desc = flag.description.strip().rstrip(".")
    evidence = flag.evidence.strip().rstrip(".")
    parts = [
        hook,
        f"{desc}.",
        f"The receipt: {evidence}.",
        "Pulled from official public records — not rumors.",
    ]
    if flag.recommended_action:
        parts.append(f"Watch for: {flag.recommended_action.strip().rstrip('.')}.")
    parts.append(
        f"If you live in {county} County, save this and ask your officials for an explanation."
    )
    return " ".join(parts)


def _cta_for_flag(flag: RedFlag, county: str) -> str:
    return (
        f"If you're in {county} County, share this with someone who pays property taxes. "
        "Full receipts are in the linked data package."
    )


def build_short_scripts(
    flags: list[RedFlag],
    county: str,
    *,
    max_scripts: int = MAX_SCRIPTS,
    min_engagement: float = MIN_ENGAGEMENT,
) -> tuple[list[ShortScript], int]:
    """Generate ShortScripts from ranked red flags. Returns (scripts, pruned_count)."""
    ranked = _rank_flags(_dedupe_flags(flags))
    scripts: list[ShortScript] = []
    pruned = 0

    used_categories: set[str] = set()
    for idx, (flag, score) in enumerate(ranked):
        if score < min_engagement:
            pruned += 1
            continue
        if len(scripts) >= max_scripts:
            break
        # Prefer one script per category for variety (salary + budget + disbursement, etc.)
        if flag.category in used_categories and len(scripts) < max_scripts - 1:
            continue

        slug = f"{county.lower().replace(' ', '-')}-{flag.category}-{idx + 1}"
        hook = _hook_for_flag(flag, county)
        script = ShortScript(
            slug=slug,
            platform="shorts",
            title=_title_for_flag(flag, county),
            hook=hook,
            script=_script_body(flag, county, hook),
            call_to_action=_cta_for_flag(flag, county),
            source_flag_category=flag.category,
            engagement_score=round(score, 2),
            provenance=flag.evidence[:500],
        )
        scripts.append(script)
        used_categories.add(flag.category)

    # Fill remaining slots if category diversity left gaps
    if len(scripts) < max_scripts:
        for idx, (flag, score) in enumerate(ranked):
            if score < min_engagement or len(scripts) >= max_scripts:
                break
            if any(s.provenance == flag.evidence[:500] for s in scripts):
                continue
            hook = _hook_for_flag(flag, county)
            scripts.append(
                ShortScript(
                    slug=f"{county.lower().replace(' ', '-')}-{flag.category}-fill-{idx + 1}",
                    platform="shorts",
                    title=_title_for_flag(flag, county),
                    hook=hook,
                    script=_script_body(flag, county, hook),
                    call_to_action=_cta_for_flag(flag, county),
                    source_flag_category=flag.category,
                    engagement_score=round(score, 2),
                    provenance=flag.evidence[:500],
                )
            )

    if not scripts and ranked:
        flag, score = ranked[0]
        hook = _hook_for_flag(flag, county)
        scripts.append(
            ShortScript(
                slug=f"{county.lower()}-fallback-1",
                platform="shorts",
                title=_title_for_flag(flag, county),
                hook=hook,
                script=_script_body(flag, county, hook),
                call_to_action=_cta_for_flag(flag, county),
                source_flag_category=flag.category,
                engagement_score=round(max(score, 0.7), 2),
                provenance=flag.evidence[:500],
            )
        )

    return scripts, pruned


class ContentStudioAgent:
    """Faceless channel scriptwriter — provenance-first, no invented numbers."""

    SOUL_PATH = Path(__file__).parent / "content_studio" / "SOUL.md"

    def __init__(self, settings: Any | None = None, session: Session | None = None):
        self.settings = settings or get_settings()
        self.session = session
        self.security: SecurityManager | None = None
        if self.session:
            self.security = SecurityManager(self.session.base_dir, self.session.session_id)
            soul_text = self.session.load_soul("content_studio", self.SOUL_PATH)
            self.session.log(f"Content Studio SOUL loaded (len={len(soul_text)} chars)")

    def run(
        self,
        research: ResearchPackage,
        analysis: AnalysisPackage,
        compliance: CompliancePackage | None = None,
    ) -> ContentStudioOutput:
        if self.session:
            self.session.log(f"Content Studio starting on analysis {analysis.id}")
            if self.security:
                self.security.record_action(
                    "script_generate",
                    {"analysis_id": analysis.id, "county": analysis.county},
                )

        flags: list[RedFlag] = []
        if compliance:
            flags.extend(compliance.red_flags)
        flags.extend(analysis.red_flags)

        scripts, pruned = build_short_scripts(flags, analysis.county)

        titles = [s.title for s in scripts]
        for angle in analysis.content_angles[:6]:
            if angle and angle not in titles:
                titles.append(angle)

        output = ContentStudioOutput(
            county=analysis.county,
            primary_area=analysis.primary_area,
            short_scripts=scripts,
            video_title_ideas=titles[:12],
            scripts_pruned=pruned,
            summary=(
                f"Generated {len(scripts)} Shorts scripts from {len(flags)} flags "
                f"({pruned} pruned below {MIN_ENGAGEMENT} engagement)."
            ),
        )

        if self.session:
            self.session.write_handoff("content_studio", output)
            self.session.log(output.summary)

        return output

    def run_from_session(self, session_path: Path | None = None) -> ContentStudioOutput:
        """Load handoffs from disk (for standalone / OpenClaw invocation)."""
        base = session_path or (self.session.base_dir if self.session else None)
        if base is None:
            raise ValueError("No session path available")

        handoffs = base / "handoffs"
        research = ResearchPackage.model_validate_json((handoffs / "researcher.json").read_text())
        analysis = AnalysisPackage.model_validate_json((handoffs / "analyst.json").read_text())
        compliance = None
        comp_path = handoffs / "silent_auditor.json"
        if comp_path.exists():
            compliance = CompliancePackage.model_validate_json(comp_path.read_text())
        return self.run(research, analysis, compliance)
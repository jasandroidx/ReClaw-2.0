"""
Adapt ReClaw handoff packages → scriptwriter AuditResult shape.

Works with AnalysisPackage / CompliancePackage red flags without requiring
tools.local_auditor_live (Silent Auditor / Perplexity build can plug in later).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.handoff import AnalysisPackage, CompliancePackage, RedFlag, ResearchPackage

# Pike County IN — ACS 5-year approximations for script context beats
COUNTY_CENSUS: dict[str, dict] = {
    "Pike": {
        "population": 12_201,
        "median_hh_income": 52_341,
        "median_earnings": 38_500,
        "poverty_rate_pct": 11.8,
    },
}


@dataclass
class AuditResult:
    """Minimal AuditResult for tools.scriptwriter — red_flags + county + census."""

    county: str
    red_flags: list[RedFlag]
    census: dict = field(default_factory=dict)
    state: str = "IN"


def build_audit_result(
    analysis: AnalysisPackage,
    research: ResearchPackage | None = None,
    compliance: CompliancePackage | None = None,
) -> AuditResult:
    flags: list[RedFlag] = []
    if compliance:
        flags.extend(compliance.red_flags)
    flags.extend(analysis.red_flags)

    county_label = analysis.county
    if not county_label.endswith("County"):
        county_label = f"{county_label} County"

    census = dict(COUNTY_CENSUS.get(analysis.county, {}))
    if research and research.median_assessed:
        census.setdefault("median_assessed_sample", research.median_assessed)

    return AuditResult(county=county_label, red_flags=flags, census=census, state="IN")
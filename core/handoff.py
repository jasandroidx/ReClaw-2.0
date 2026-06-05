"""
Handoff + Event models — the contract between agents and for future visual frontend.

All agents exchange ONLY these structured types (or their .model_dump_json()).
This guarantees clean, auditable, replayable pipelines. The AgentEvent model is the first-class JSON contract for the visual agent office layer (Phase 1 prep only).

Production notes:
- Use Pydantic for validation + serialization.
- Every package carries 'id', 'timestamp', 'provenance' for traceability.
- Red flags and insights are the "money" — what the faceless channel actually uses.
- Keep fields minimal but complete for Obsidian rendering + future LLM scriptwriter.
- Event model supports real-time state (disk-based, no in-memory reliance).
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SourceRef(BaseModel):
    """Where a piece of data came from."""
    kind: Literal["seed", "web", "pdf", "api", "manual"] = "seed"
    url: str | None = None
    note: str | None = None
    fetched_at: datetime = Field(default_factory=now_utc)


class PropertyRecord(BaseModel):
    """Public property / tax record (rural focus)."""
    parcel_id: str
    address: str
    city: str = "Winslow"
    county: str = "Pike"
    state: str = "IN"
    zip_code: str = "47598"
    land_acres: float | None = None
    assessed_value: int | None = None  # total assessed
    land_value: int | None = None
    improvement_value: int | None = None
    property_class: str | None = None  # ag, residential, etc.
    year_built: int | None = None
    owner_name: str | None = None  # may be redacted in prod
    last_sale_date: str | None = None
    last_sale_price: int | None = None
    notes: str | None = None


class BudgetData(BaseModel):
    """County / local gov budget snapshot."""
    fiscal_year: int
    entity: str  # "Pike County", "Winslow Town", etc.
    total_revenue: int | None = None
    total_expenditures: int | None = None
    surplus_deficit: int | None = None
    major_funds: dict[str, int] = Field(default_factory=dict)  # e.g. {"General": 2450000, "Road": 980000}
    revenue_sources: dict[str, int] = Field(default_factory=dict)
    expenditure_categories: dict[str, int] = Field(default_factory=dict)
    notes: str | None = None
    source: SourceRef | None = None


class SalaryEntry(BaseModel):
    """Public salary / payroll transparency record."""
    department: str
    position: str
    employee_count: int | None = None
    avg_salary: int | None = None
    min_salary: int | None = None
    max_salary: int | None = None
    total_payroll: int | None = None
    year: int
    notes: str | None = None


class ResearchPackage(BaseModel):
    """
    Output of Researcher Agent.
    This is the handoff artifact passed to Analyst/RedFlag and Orchestrator.
    """
    id: str = Field(default_factory=lambda: f"research-{uuid4().hex[:12]}")
    county: str
    primary_area: str  # "Winslow", "Patoka Lake", etc.
    state: str = "IN"
    fetched_at: datetime = Field(default_factory=now_utc)
    sources: list[SourceRef] = Field(default_factory=list)
    property_records: list[PropertyRecord] = Field(default_factory=list)
    budgets: list[BudgetData] = Field(default_factory=list)
    salaries: list[SalaryEntry] = Field(default_factory=list)
    summary: str = ""  # 3-6 sentence plain English from researcher
    raw_excerpts: list[str] = Field(default_factory=list)  # notable quotes or table rows

    @property
    def total_properties(self) -> int:
        return len(self.property_records)

    @property
    def median_assessed(self) -> int | None:
        vals = [p.assessed_value for p in self.property_records if p.assessed_value]
        if not vals:
            return None
        vals.sort()
        n = len(vals)
        return vals[n // 2] if n % 2 else (vals[n//2 - 1] + vals[n//2]) // 2


class Insight(BaseModel):
    """Actionable rural data insight suitable for content or decision making."""
    category: Literal["property", "budget", "demographics", "economy", "infrastructure", "opportunity"]
    title: str
    detail: str
    supporting_numbers: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    suggested_angle: str | None = None  # for faceless channel hook


class RedFlag(BaseModel):
    """Something that looks off, risky, or worth deeper investigation."""
    severity: Literal["low", "medium", "high", "critical"]
    category: str
    description: str
    evidence: str
    recommended_action: str | None = None  # "watch 2026 budget vote", "pull more parcels in zip 47598"


class AnalysisPackage(BaseModel):
    """
    Output of Analyst / Red Flag Agent.
    This is the second handoff. Orchestrator merges Research + Analysis.
    """
    id: str = Field(default_factory=lambda: f"analysis-{uuid4().hex[:12]}")
    research_id: str
    county: str
    primary_area: str
    generated_at: datetime = Field(default_factory=now_utc)
    insights: list[Insight] = Field(default_factory=list)
    red_flags: list[RedFlag] = Field(default_factory=list)
    budget_implications: list[str] = Field(default_factory=list)
    content_angles: list[str] = Field(default_factory=list)  # ready-to-use for scriptwriter
    overall_risk_score: float = Field(ge=0.0, le=10.0, default=3.0)
    summary: str = ""


class ContentPackage(BaseModel):
    """
    Final assembled package from Orchestrator.
    This is what gets written to Obsidian and (later) fed to Scriptwriter/Visuals.
    """
    id: str = Field(default_factory=lambda: f"pkg-{uuid4().hex[:12]}")
    county: str
    primary_area: str
    generated_at: datetime = Field(default_factory=now_utc)
    research: ResearchPackage
    analysis: AnalysisPackage
    obsidian_filename: str | None = None  # set by writer
    tags: list[str] = Field(default_factory=lambda: ["rural-data", "pike", "faceless-channel"])
    video_title_ideas: list[str] = Field(default_factory=list)
    key_stats: dict[str, Any] = Field(default_factory=dict)  # for voiceover / thumbnails

# Future visual office / agent frontend event contract (first-class, disk-based)
# Consumed by visual layer (out of Phase 1 scope). Emitted by Gateway/Session for real-time state.
class AgentEvent(BaseModel):
    """JSON event/state contract for future visual agent office layer."""
    agent_id: str
    role: str  # e.g. "researcher", "analyst", "orchestrator", "gateway"
    state: str  # e.g. "running", "completed", "failed", "awaiting_approval"
    current_task: str | None = None
    started_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    last_result: dict[str, Any] | None = None
    last_error: str | None = None
    run_id: str | None = None  # links to session/run

    def to_json(self) -> dict:
        return self.model_dump(mode="json")

    def to_obsidian_frontmatter(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "county": self.county,
            "area": self.primary_area,
            "date": self.generated_at.date().isoformat(),
            "research_id": self.research.id,
            "analysis_id": self.analysis.id,
            "tags": self.tags,
            "risk_score": self.analysis.overall_risk_score,
        }

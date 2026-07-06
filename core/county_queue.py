"""
Indiana county video queue — one county at a time, human approval gate.

Flow: run_next → audit + scripts → pending review → approve/reject → advance cursor.
Rejections are logged with reason for revisit (option b).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import yaml
from pydantic import BaseModel, Field

from core.config import get_settings
from core.handoff import (
    AnalysisPackage,
    ContentPackage,
    ContentStudioOutput,
    LongFormScript,
    ResearchPackage,
    ShortScript,
)
from agents.content_studio import ContentStudioAgent, _shorts_from_scriptwriter
from agents.orchestrator import Orchestrator
from core.session import Session, create_session
from tools.audit_adapter import build_audit_result
from tools.county_gateway_audit import audit_county_gateway
from tools.scriptwriter import DISCLAIMER, build_package, build_script, long_form_worthiness

QUEUE_DIR = Path(__file__).resolve().parent.parent / "data" / "county_queue"
STATE_PATH = QUEUE_DIR / "state.json"
WORKLIST_PATH = Path(__file__).resolve().parent.parent / "data" / "indiana_county_worklist.yaml"
REVIEW_DIR = QUEUE_DIR / "pending"


class CountyWorkItem(BaseModel):
    gateway_code: int
    name: str
    fips: str
    worklist_position: int
    geo_push: str = ""
    distance_from_pike_mi: float | None = None


class ReviewCard(BaseModel):
    """Human review surface — one county, both formats ready."""

    id: str = Field(default_factory=lambda: f"review-{uuid4().hex[:12]}")
    county: str
    gateway_code: int
    fips: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["pending_approval", "approved", "rejected"] = "pending_approval"
    risk_score: float = 0.0
    flag_count: int = 0
    top_finding: str = ""
    top_category: str | None = None
    recommendation: str = ""
    long_form_worthy: bool = False
    long_form_runtime_min: float | None = None
    worthiness_score: int = 0
    worthiness_reasons: list[str] = Field(default_factory=list)
    geo_push: str = ""
    short_count: int = 0
    top_short_hook: str | None = None
    package_id: str | None = None
    session_id: str | None = None
    obsidian_file: str | None = None
    run_artifact: str | None = None
    reject_reason: str | None = None
    publish_formats: list[str] = Field(default_factory=lambda: ["shorts"])


class QueueState(BaseModel):
    cursor: int = 0
    status: Literal["idle", "awaiting_approval", "processing"] = "idle"
    pending_review: ReviewCard | None = None
    last_completed: str | None = None
    approved_count: int = 0
    rejected_count: int = 0
    history: list[dict[str, Any]] = Field(default_factory=list)
    rejections: list[dict[str, Any]] = Field(default_factory=list)


class CountyQueue:
    def __init__(self, settings: Any | None = None):
        self.settings = settings or get_settings()
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        self.worklist = self._load_worklist()

    def _load_worklist(self) -> list[CountyWorkItem]:
        if not WORKLIST_PATH.exists():
            from scripts.build_indiana_worklist import main as build_wl

            build_wl()
        data = yaml.safe_load(WORKLIST_PATH.read_text())
        return [CountyWorkItem(**c) for c in data.get("counties", [])]

    def load_state(self) -> QueueState:
        if STATE_PATH.exists():
            return QueueState.model_validate_json(STATE_PATH.read_text())
        return QueueState()

    def save_state(self, state: QueueState) -> None:
        STATE_PATH.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def status(self) -> dict[str, Any]:
        state = self.load_state()
        current = self.worklist[state.cursor] if state.cursor < len(self.worklist) else None
        return {
            "queue_status": state.status,
            "cursor": state.cursor,
            "total_counties": len(self.worklist),
            "current_county": current.model_dump() if current else None,
            "next_county": (
                self.worklist[state.cursor].model_dump()
                if state.status == "idle" and state.cursor < len(self.worklist)
                else None
            ),
            "pending_review": (
                state.pending_review.model_dump(mode="json") if state.pending_review else None
            ),
            "approved_count": state.approved_count,
            "rejected_count": state.rejected_count,
            "remaining": max(0, len(self.worklist) - state.cursor),
        }

    def _write_review_obsidian(self, card: ReviewCard, pkg: ContentPackage | None = None) -> Path:
        vault = self.settings.effective_obsidian_path
        vault.mkdir(parents=True, exist_ok=True)
        date = card.created_at.strftime("%Y-%m-%d")
        slug = card.county.lower().replace(" ", "-").replace("county", "").strip("-")
        path = vault / f"{date}-review-{slug}-county.md"
        lines = [
            "---",
            f"id: {card.id}",
            f"county: {card.county}",
            f"gateway_code: {card.gateway_code}",
            f"fips: {card.fips}",
            f"status: {card.status}",
            f"recommendation: {card.recommendation}",
            f"long_form_worthy: {card.long_form_worthy}",
            "tags: [county-queue, review-card, faceless-channel]",
            "---",
            f"# Review Card — {card.county}",
            "",
            f"**Status:** `{card.status}` · **Flags:** {card.flag_count} · **Risk:** {card.risk_score}/10",
            "",
            "## Recommendation",
            card.recommendation,
            "",
            "## Top Finding",
            card.top_finding,
            "",
            "## Geo Push",
            card.geo_push,
            "",
            "## Shorts",
            f"- Count: {card.short_count}",
            f"- Top hook: {card.top_short_hook or 'n/a'}",
            "",
        ]
        if card.long_form_worthy:
            lines.extend(
                [
                    "## Long-Form",
                    f"- Runtime: ~{card.long_form_runtime_min} min",
                    f"- Worthiness score: {card.worthiness_score}",
                    "- Reasons: " + "; ".join(card.worthiness_reasons),
                    "",
                ]
            )
        if pkg and pkg.obsidian_filename:
            lines.append(f"Full package: [[{pkg.obsidian_filename}]]")
        lines.append("\n---\n*Approve via POST /county-queue/approve or reject with reason.*\n")
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _run_full_county_pipeline(self, item: CountyWorkItem) -> tuple[ContentPackage, Session]:
        """Full researcher → auditor → analyst → content studio for any county."""
        area = item.name if item.name != "Pike" else "Winslow"
        sess, _ = create_session(item.name, area, write_to_obsidian=True)
        pkg = Orchestrator(self.settings, session=sess).run_county(
            county=item.name, area=area, write_to_obsidian=True
        )
        return pkg, sess

    def _run_gateway_county(self, item: CountyWorkItem) -> tuple[ContentPackage, Session, ContentStudioOutput]:
        sess, _ = create_session(item.name, item.name, write_to_obsidian=False)
        audit = audit_county_gateway(item.gateway_code, item.name)
        pkg_data = build_package(audit, county=audit.county)

        analysis = AnalysisPackage(
            research_id=f"gw-{item.gateway_code}",
            county=item.name,
            primary_area=item.name,
            red_flags=audit.red_flags,
            overall_risk_score=min(10.0, 2.0 + len(audit.red_flags) * 1.5),
            summary=f"Gateway audit {item.name}: {len(audit.red_flags)} flags",
        )
        research = ResearchPackage(
            county=item.name,
            primary_area=item.name,
            summary=f"Indiana Gateway disbursement audit for {item.name} County.",
            sources=[],
        )

        long_form = None
        if pkg_data.get("long_form"):
            lf = pkg_data["long_form"]
            long_form = LongFormScript(
                markdown=lf["markdown"],
                words=lf.get("words", 0),
                runtime_min=lf.get("runtime_min", 0.0),
                titles=lf.get("titles", []),
                worthy=True,
                worthiness_score=pkg_data["worthiness_score"],
                worthiness_reasons=pkg_data["worthiness_reasons"],
                disclaimer=DISCLAIMER,
            )

        shorts, dist = _shorts_from_scriptwriter(audit, item.name, max_shorts=5)
        studio_out = ContentStudioOutput(
            county=item.name,
            primary_area=item.name,
            short_scripts=shorts,
            long_form=long_form,
            distribution_meta=dist,
            video_title_ideas=long_form.titles if long_form else [s.hook for s in shorts],
            summary=pkg_data["recommendation"],
        )
        sess.write_handoff("content_studio", studio_out)

        pkg = ContentPackage(
            county=item.name,
            primary_area=item.name,
            research=research,
            analysis=analysis,
            short_scripts=shorts,
            long_form=long_form,
            video_title_ideas=studio_out.video_title_ideas,
            approval_status="pending_approval",
            key_stats={
                "flag_count": len(audit.red_flags),
                "short_scripts": len(shorts),
                "long_form_worthy": bool(long_form),
                "gateway_code": item.gateway_code,
            },
        )

        from core.obsidian_writer import ObsidianWriter

        md_path = ObsidianWriter(self.settings).write_package(pkg)
        pkg.obsidian_filename = md_path.name
        return pkg, sess, studio_out

    def run_next(self, *, force: bool = False) -> dict[str, Any]:
        state = self.load_state()
        if state.status == "awaiting_approval" and state.pending_review and not force:
            return {
                "ok": False,
                "message": "Awaiting approval on current county. Approve or reject before advancing.",
                "pending_review": state.pending_review.model_dump(mode="json"),
            }
        if state.cursor >= len(self.worklist):
            return {"ok": False, "message": "Worklist complete.", "cursor": state.cursor}

        item = self.worklist[state.cursor]
        state.status = "processing"
        self.save_state(state)

        try:
            pkg, sess = self._run_full_county_pipeline(item)
            studio_summary = (
                f"{len(pkg.short_scripts)} shorts"
                + (
                    f" + long-form ~{pkg.long_form.runtime_min}min"
                    if pkg.long_form and pkg.long_form.worthy
                    else ""
                )
            )
            worthy = bool(pkg.long_form and pkg.long_form.worthy)
            runtime = pkg.long_form.runtime_min if pkg.long_form else None
            reasons = pkg.long_form.worthiness_reasons if pkg.long_form else []
            wscore = pkg.long_form.worthiness_score if pkg.long_form else 0
            top_hook = pkg.short_scripts[0].hook if pkg.short_scripts else None
            top_cat = pkg.short_scripts[0].source_flag_category if pkg.short_scripts else None
            top_find = pkg.analysis.red_flags[0].description if pkg.analysis.red_flags else ""
            recommendation = (
                f"STRONG long-form (~{runtime} min) + {len(pkg.short_scripts)} shorts"
                if worthy
                else f"Shorts focus — {len(pkg.short_scripts)} hooks"
            )

            card = ReviewCard(
                county=item.name,
                gateway_code=item.gateway_code,
                fips=item.fips,
                risk_score=pkg.analysis.overall_risk_score,
                flag_count=len(pkg.analysis.red_flags),
                top_finding=top_find,
                top_category=top_cat,
                recommendation=recommendation,
                long_form_worthy=worthy,
                long_form_runtime_min=runtime,
                worthiness_score=wscore,
                worthiness_reasons=reasons,
                geo_push=item.geo_push,
                short_count=len(pkg.short_scripts),
                top_short_hook=top_hook,
                package_id=pkg.id,
                session_id=sess.session_id,
                obsidian_file=pkg.obsidian_filename,
                publish_formats=(
                    ["long_form", "shorts"] if worthy else ["shorts"]
                ),
            )
            review_path = self._write_review_obsidian(card, pkg)
            card.obsidian_file = review_path.name

            state.pending_review = card
            state.status = "awaiting_approval"
            self.save_state(state)

            return {
                "ok": True,
                "message": f"County {item.name} ready for review. {studio_summary}",
                "review_card": card.model_dump(mode="json"),
                "worklist_position": state.cursor,
                "review_obsidian": str(review_path),
            }
        except Exception as e:
            state.status = "idle"
            self.save_state(state)
            raise RuntimeError(f"County queue run failed for {item.name}: {e}") from e

    def approve(
        self,
        *,
        publish_formats: list[str] | None = None,
        granted_by: str = "human",
    ) -> dict[str, Any]:
        state = self.load_state()
        if not state.pending_review:
            raise ValueError("No pending review to approve.")
        card = state.pending_review
        card.status = "approved"
        if publish_formats:
            card.publish_formats = publish_formats

        entry = {
            "action": "approved",
            "county": card.county,
            "gateway_code": card.gateway_code,
            "review_id": card.id,
            "at": datetime.now(timezone.utc).isoformat(),
            "granted_by": granted_by,
            "publish_formats": card.publish_formats,
            "package_id": card.package_id,
        }
        state.history.append(entry)
        state.approved_count += 1
        state.last_completed = card.county
        state.pending_review = None
        state.cursor += 1
        state.status = "idle"
        self.save_state(state)

        next_item = (
            self.worklist[state.cursor].model_dump()
            if state.cursor < len(self.worklist)
            else None
        )
        return {
            "ok": True,
            "message": f"Approved {card.county}. Cursor advanced to position {state.cursor}.",
            "next_county": next_item,
            "approved": entry,
        }

    def reject(self, reason: str, *, granted_by: str = "human") -> dict[str, Any]:
        state = self.load_state()
        if not state.pending_review:
            raise ValueError("No pending review to reject.")
        card = state.pending_review
        card.status = "rejected"
        card.reject_reason = reason

        entry = {
            "action": "rejected",
            "county": card.county,
            "gateway_code": card.gateway_code,
            "review_id": card.id,
            "reason": reason,
            "at": datetime.now(timezone.utc).isoformat(),
            "granted_by": granted_by,
            "package_id": card.package_id,
            "revisit": True,
        }
        state.rejections.append(entry)
        state.history.append(entry)
        state.rejected_count += 1
        state.pending_review = None
        state.cursor += 1
        state.status = "idle"
        self.save_state(state)

        next_item = (
            self.worklist[state.cursor].model_dump()
            if state.cursor < len(self.worklist)
            else None
        )
        return {
            "ok": True,
            "message": f"Rejected {card.county} (logged for revisit). Cursor advanced.",
            "reason": reason,
            "next_county": next_item,
            "rejection": entry,
        }
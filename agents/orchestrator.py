"""
Light Orchestrator — ReClaw 2.0

Coordinates the minimal swarm:
    Researcher → Analyst/RedFlag → assemble ContentPackage → (optional) Obsidian write

Responsibilities:
- Own the end-to-end flow for one county/area run.
- Persist raw JSON artifacts to data/runs/ for audit / replay.
- Call ObsidianWriter when requested.
- Return a single ContentPackage that downstream (API, Discord bot, Scriptwriter) can trust.

This is intentionally "dumb but reliable". No fancy DAGs yet. Add when we have 5+ agents.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config import get_settings
from core.handoff import ContentPackage
from .researcher import ResearcherAgent
from .analyst import AnalystAgent
from core.obsidian_writer import ObsidianWriter
from core.session import Session, create_session
from core.security import SecurityManager


class Orchestrator:
    """
    Light Orchestrator with quality gates.

    OpenClaw style:
    - Owns the full pipeline for a county run
    - Creates or receives a Session for isolation
    - Enforces the quality gates defined in SOUL.md before publishing
    - Loads system + agent identities
    - Delegates to agents (which do their own handoff writes)
    - Final durable outputs: runs/ JSON + Obsidian .md via channel
    """

    SOUL_PATH = Path(__file__).parent.parent / "SOUL.md"

    def __init__(self, settings: Any | None = None, session: Session | None = None):
        self.settings = settings or get_settings()
        self.session = session
        self.security: SecurityManager | None = None

        if self.session:
            self.security = SecurityManager(self.session.base_dir, self.session.session_id)
            # Load the swarm SOUL for provenance
            soul = self.session.load_soul("orchestrator", self.SOUL_PATH)
            self.session.log(f"Orchestrator (swarm SOUL) loaded")

        # Agents are created with the same session so they participate in isolation + security
        self.researcher = ResearcherAgent(self.settings, session=self.session)
        self.analyst = AnalystAgent(self.settings, session=self.session)
        self.writer = ObsidianWriter(self.settings)

    def run_county(
        self,
        county: str = "Pike",
        area: str = "Winslow",
        write_to_obsidian: bool = True,
        dry_run: bool = False,
    ) -> ContentPackage:
        """
        Full pipeline with quality gates.
        """
        if self.session:
            self.session.log(f"Orchestrator pipeline start: {county}/{area}")
        else:
            print(f"[Orchestrator] Starting run for {county} / {area}... (no session - consider using create_session for full audit)")

        # 1. Researcher
        research = self.researcher.run(county=county, area=area)
        print(f"[Orchestrator] Research complete: {research.id} ({research.total_properties} props, {len(research.budgets)} budgets)")

        # 2. Analyst
        analysis = self.analyst.run(research)
        print(f"[Orchestrator] Analysis complete: {analysis.id} | risk={analysis.overall_risk_score} | flags={len(analysis.red_flags)}")

        # 3. Quality gates (from SOUL.md)
        self._enforce_quality_gates(research, analysis)

        pkg = self._assemble_package(research, analysis)

        # Persist full package (audit)
        artifact_path = self._save_run_artifact(pkg)
        if self.session:
            self.session.log(f"ContentPackage assembled and saved to {artifact_path}")

        # 4. Channel write (Obsidian is the primary durable channel)
        if write_to_obsidian:
            md_path = self.writer.write_package(pkg, dry_run=dry_run)
            print(f"[Orchestrator] Obsidian package written: {md_path}")
            if self.session:
                self.session.log(f"Published to Obsidian: {md_path}")
        else:
            print("[Orchestrator] Skipping Obsidian write (write_to_obsidian=False)")

        if self.session:
            self.session.log("Orchestrator pipeline complete.")
        return pkg

    def _enforce_quality_gates(self, research, analysis) -> None:
        """Hard gates. Abort or mark if violated."""
        errors = []
        if research.total_properties < 1 and len(research.budgets) < 1:
            errors.append("ResearchPackage has insufficient data (no properties and no budgets)")

        if len(analysis.red_flags) == 0 and len(analysis.insights) < 2:
            errors.append("AnalysisPackage is too thin — needs at least 1 red_flag or 2 insights")

        if analysis.overall_risk_score > 8:
            errors.append(f"Risk score {analysis.overall_risk_score} is very high. Manual review recommended before Obsidian publish.")

        if errors:
            msg = "QUALITY GATE FAILURES: " + " | ".join(errors)
            if self.session:
                self.session.log(msg, level="WARN")
            print(f"[Orchestrator] {msg}")
            # In production we might still allow the package but flag it heavily.
            # For now we attach the note to the package via a side effect on analysis (simple).
            analysis.summary = analysis.summary + " | GATE WARNING: " + msg

    def _assemble_package(self, research, analysis) -> ContentPackage:
        pkg = ContentPackage(
            county=research.county,
            primary_area=research.primary_area,
            research=research,
            analysis=analysis,
        )

        # Derive some easy key_stats + title ideas here (orchestrator owns final polish)
        pkg.key_stats = {
            "properties_analyzed": research.total_properties,
            "median_assessed_value": f"${research.median_assessed:,}" if research.median_assessed else "N/A",
            "red_flags": len(analysis.red_flags),
            "insights": len(analysis.insights),
            "budget_deficit": any((b.surplus_deficit or 0) < 0 for b in research.budgets),
        }

        # Strong video titles for faceless channel (rural data / personal finance / prepping adjacent)
        pkg.video_title_ideas = analysis.content_angles + [
            f"Pike County Indiana 2026: The $25k House Is Real (But Here's What It Costs You)",
            f"Why Rural Counties Are Quietly Raising Taxes While Property Values Stay Flat",
            f"47 Acres for $124k in Southern Indiana — Would You Buy It?",
        ]

        return pkg

    def _save_run_artifact(self, pkg: ContentPackage) -> Path:
        runs_dir = self.settings.runs_dir
        runs_dir.mkdir(parents=True, exist_ok=True)
        ts = pkg.generated_at.strftime("%Y%m%d_%H%M%S")
        fname = f"{ts}_{pkg.id}.json"
        path = runs_dir / fname
        path.write_text(pkg.model_dump_json(indent=2), encoding="utf-8")

        # If we have a session, archive its full contents (isolation proof + audit)
        if self.session:
            try:
                self.session.archive(runs_dir)
            except Exception as e:
                print(f"[Orchestrator] Session archive warning: {e}")
        return path

    def close(self):
        """Cleanup clients if needed."""
        self.researcher.close()

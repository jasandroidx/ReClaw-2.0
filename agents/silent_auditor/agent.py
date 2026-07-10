"""
Silent Auditor Agent — ReClaw 2.0 (real implementation)

Performs deep compliance, red-flag, and budget anomaly audits for counties.
Uses detector modules + RULEBOOK.yml configuration. Writes CompliancePackage handoff.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.config import get_settings
from core.handoff import CompliancePackage, RedFlag
from core.security import SecurityManager
from core.session import Session

from agents.silent_auditor.detectors import AuditData, run_all
from agents.silent_auditor.detectors.base import load_rulebook


class SilentAuditorAgent:
    """
    Real Silent Auditor Agent.

    - Loads agents/silent_auditor/SOUL.md via session
    - Checks 'compliance_audit' capability (HIGH risk)
    - Runs detector suite from RULEBOOK.yml
    - Writes CompliancePackage handoff
    """

    SOUL_PATH = Path(__file__).parent / "silent_auditor" / "SOUL.md"  # agents/silent_auditor/SOUL.md

    def __init__(self, settings: Any | None = None, session: Session | None = None):
        self.settings = settings or get_settings()
        self.session = session
        self.security: SecurityManager | None = None
        if self.session:
            self.security = SecurityManager(self.session.base_dir, self.session.session_id)
            soul_text = self.session.load_soul("silent_auditor", self.SOUL_PATH)
            self.session.log(f"Silent Auditor SOUL loaded (len={len(soul_text)} chars)")

    def run(self, county: str, gateway_code: int | None = None) -> CompliancePackage | None:
        if self.session:
            self.session.log(f"Silent Auditor starting audit for county: {county}")
            if self.security:
                if not self.security.is_granted("compliance_audit"):
                    self.session.log("Awaiting approval for compliance_audit", level="WARN")
                    self.security.request_approval(
                        capability="compliance_audit",
                        reason=f"Run full detector suite on {county} disbursements and federal data.",
                        agent="silent_auditor",
                    )
                    raise PermissionError("Capability 'compliance_audit' required but not granted.")

                self.security.record_action("compliance_audit", {"county": county})

        # Build audit input
        from tools.county_data_fetch import resolve_county

        meta = resolve_county(county) or {}
        gc = gateway_code or meta.get("gateway_code")
        ad = AuditData(county=county, gateway_code=gc)

        # Run detectors
        raw_flags = run_all(ad)

        # Dedupe + score
        seen = set()
        flags: list[RedFlag] = []
        for f in raw_flags:
            key = f"{f.category}:{f.description[:80]}"
            if key in seen:
                continue
            seen.add(key)
            flags.append(f)

        high = sum(1 for f in flags if f.severity in ("critical", "high"))
        risk = min(10.0, 2.0 + high * 1.8 + len(flags) * 0.4)

        pkg = CompliancePackage(
            county=county,
            red_flags=flags,
            overall_risk_score=round(risk, 1),
            summary=f"Silent Auditor (detector suite): {len(flags)} flags for {county}.",
            source_file="agents/silent_auditor/detectors",
            total_records_audited=len(flags),
        )

        if self.session:
            self.session.write_handoff("silent_auditor", pkg)
            self.session.log(f"Silent Auditor complete. {len(flags)} flags, risk={risk:.1f}")

        return pkg

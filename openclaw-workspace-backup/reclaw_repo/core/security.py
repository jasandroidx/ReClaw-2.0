"""
Security & Permissions — ReClaw 2.0 (OpenClaw-aligned least privilege + approval gates)

This module is the enforcement layer. Agents never get blanket power.

Key concepts:
- RiskLevel: low | medium | high
- Capability: a named thing an agent can do (e.g. "public_data_live_fetch")
- SessionPermissionGrant: recorded proof that a gate was passed for this session
- Approval request flow for anything high-risk or not pre-granted

MVP implementation is file-based (writes pending/ and granted/ files into the session dir).
This makes everything auditable and works even if the process restarts.

In Docker: the container for agents can be run with read-only root fs + limited volume mounts
(gateway controls what the agent process sees).

Future: integrate with actual container security (seccomp, AppArmor, user namespaces) + Tailscale identity for who approved.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .config import get_settings


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Capability(BaseModel):
    name: str
    risk: RiskLevel
    description: str
    requires_approval: bool = False   # if True, even medium may need gate depending on policy


# Declared capabilities for the current swarm (central registry — agents must match these)
DECLARED_CAPABILITIES: dict[str, Capability] = {
    "public_data_seed": Capability(
        name="public_data_seed",
        risk=RiskLevel.LOW,
        description="Read local seed JSON files for counties. Always safe.",
    ),
    "public_data_live_fetch": Capability(
        name="public_data_live_fetch",
        risk=RiskLevel.MEDIUM,
        description="Perform live HTTP requests to county .gov / GIS sites. Can be noisy and reveals our IP.",
        requires_approval=True,
    ),
    "heuristic_analysis": Capability(
        name="heuristic_analysis",
        risk=RiskLevel.LOW,
        description="Run deterministic rules on a ResearchPackage.",
    ),
    "obsidian_write": Capability(
        name="obsidian_write",
        risk=RiskLevel.MEDIUM,
        description="Write final .md + .json to the configured Obsidian vault path.",
        requires_approval=False,  # controlled by config path + session
    ),
    "shell_exec": Capability(
        name="shell_exec",
        risk=RiskLevel.HIGH,
        description="Run arbitrary shell commands. Almost never granted in this swarm.",
        requires_approval=True,
    ),
    # New capabilities for Clawsmith visual agent floor (per approved plan)
    "grant_scan": Capability(
        name="grant_scan",
        risk=RiskLevel.MEDIUM,
        description="Scan grants/RFPs for Grant Hall cell. Gated for write/alert generation.",
        requires_approval=True,
    ),
    "compliance_audit": Capability(
        name="compliance_audit",
        risk=RiskLevel.HIGH,
        description="Deep compliance/red-flag audits for Silent Auditor. High risk for reports.",
        requires_approval=True,
    ),
    "job_match": Capability(
        name="job_match",
        risk=RiskLevel.MEDIUM,
        description="Local job/salary matching for Job Aggregator. Leads to paid lists.",
    ),
    "arbitrage_scan": Capability(
        name="arbitrage_scan",
        risk=RiskLevel.HIGH,
        description="Marketplace scraping for Flips cell. Gated for live data.",
        requires_approval=True,
    ),
    "script_generate": Capability(
        name="script_generate",
        risk=RiskLevel.LOW,
        description="Generate faceless content/scripts for Content Studio from packages.",
    ),
    "cell_create": Capability(
        name="cell_create",
        risk=RiskLevel.MEDIUM,
        description="Clawforge meta-action to create new room cell + memory + visual desk.",
    ),
    "visual_event_emit": Capability(
        name="visual_event_emit",
        risk=RiskLevel.LOW,
        description="Emit WS events for dashboard sprite states and board updates.",
    ),
    "memory_consolidate": Capability(
        name="memory_consolidate",
        risk=RiskLevel.LOW,
        description="Background Total-ReClaw consolidation job per cell.",
    ),
}


class ApprovalRequest(BaseModel):
    id: str = Field(default_factory=lambda: f"appr-{uuid4().hex[:8]}")
    session_id: str
    capability: str
    requested_by: str  # "researcher" or agent name
    reason: str
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"  # pending | granted | denied | expired


class SessionGrant(BaseModel):
    id: str
    capability: str
    granted_to: str
    granted_at: datetime
    granted_by: str = "gateway"  # or "auto-policy" | "human:discord:xxx"
    expires_at: datetime | None = None
    notes: str | None = None


class SecurityManager:
    """
    Per-session security context.

    Typical usage inside an agent or orchestrator:
        sec = SecurityManager(session_dir)
        if not sec.is_granted("public_data_live_fetch"):
            req = sec.request_approval("public_data_live_fetch", "need 2026 budget PDF", agent="researcher")
            # then either raise or return "awaiting approval"
        sec.record_action("public_data_live_fetch", {"url": "...", "status": 200})
    """

    def __init__(self, session_dir: Path, session_id: str):
        self.session_dir = session_dir
        self.session_id = session_id
        self.approvals_dir = session_dir / "approvals"
        self.approvals_dir.mkdir(parents=True, exist_ok=True)
        self.grants: list[SessionGrant] = []
        self._load_existing_grants()

    def _load_existing_grants(self):
        granted_dir = self.approvals_dir / "granted"
        if not granted_dir.exists():
            return
        for f in granted_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                self.grants.append(SessionGrant(**data))
            except Exception:
                pass

    def is_granted(self, capability: str) -> bool:
        cap = DECLARED_CAPABILITIES.get(capability)
        if not cap:
            return False
        if cap.risk == RiskLevel.LOW:
            return True
        # Check for an active grant
        now = datetime.now(timezone.utc)
        for g in self.grants:
            if g.capability == capability and (g.expires_at is None or g.expires_at > now):
                return True
        return False

    def request_approval(self, capability: str, reason: str, agent: str = "unknown") -> ApprovalRequest:
        req = ApprovalRequest(
            session_id=self.session_id,
            capability=capability,
            requested_by=agent,
            reason=reason,
        )
        path = self.approvals_dir / f"pending-{req.id}.json"
        path.write_text(req.model_dump_json(indent=2), encoding="utf-8")
        return req

    def grant(self, capability: str, granted_by: str = "auto", notes: str | None = None) -> SessionGrant:
        cap = DECLARED_CAPABILITIES.get(capability)
        if not cap:
            raise ValueError(f"Unknown capability: {capability}")

        grant = SessionGrant(
            id=f"grant-{uuid4().hex[:8]}",
            capability=capability,
            granted_to=self.session_id,
            granted_at=datetime.now(timezone.utc),
            granted_by=granted_by,
            notes=notes,
        )
        # persist
        granted_dir = self.approvals_dir / "granted"
        granted_dir.mkdir(exist_ok=True)
        (granted_dir / f"{grant.id}.json").write_text(grant.model_dump_json(indent=2), encoding="utf-8")
        self.grants.append(grant)
        return grant

    def record_action(self, capability: str, details: dict[str, Any]) -> None:
        """Audit log of every use of a capability."""
        log_dir = self.session_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "capability": capability,
            "details": details,
        }
        (log_dir / "security.log").open("a", encoding="utf-8").write(json.dumps(entry) + "\n")

    def get_pending_requests(self) -> list[ApprovalRequest]:
        out = []
        for f in self.approvals_dir.glob("pending-*.json"):
            try:
                out.append(ApprovalRequest(**json.loads(f.read_text())))
            except Exception:
                continue
        return out


def get_capability(name: str) -> Capability:
    if name not in DECLARED_CAPABILITIES:
        raise KeyError(f"Capability {name} not declared. Add it to DECLARED_CAPABILITIES in core/security.py")
    return DECLARED_CAPABILITIES[name]

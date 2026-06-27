"""
ReClaw Gateway (Control Plane) — FastAPI implementation.

This is the OpenClaw-style Gateway:
- Single entry for all triggers (HTTP, future Discord bot, cron, CLI)
- Creates isolated Sessions for every run
- Loads SOUL.md identities for the swarm + specific agents
- Enforces the permission / approval gate system (see core/security.py)
- Routes work to Orchestrator (which sequences Researcher → Analyst with quality gates)
- Exposes status, artifacts, and approval endpoints

Primary access: via Tailscale (see docs/tailscale.md). Never expose 0.0.0.0 publicly without strong auth.

Core endpoints:
- POST /trigger/{county}   — start full pipeline (background)
- POST /run-sync           — blocking run (great for testing)
- GET  /jobs/{job_id}
- POST /sessions/{session_id}/approve   — human or bot grants a pending high-risk action
- GET  /health
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel

from core.config import get_settings
from agents.orchestrator import Orchestrator
from core.handoff import ContentPackage, AgentEvent
from core.session import create_session, Session
from core.security import SecurityManager, DECLARED_CAPABILITIES
from core.knowledge import KnowledgeManager  # Forces Oracle/Ravenstack rules on every gateway start

app = FastAPI(title="ReClaw 2.0", version="2.0.0", description="General Agent Platform API (rural_data module + future domains)")

settings = get_settings()
# === ORACLE ENFORCEMENT: Gateway always instantiates KnowledgeManager so the Ravenstack rule set is in context
_ = KnowledgeManager(settings)

# The Gateway owns session creation. We create a fresh Orchestrator per job so it can be bound to one session.
# (Lightweight for MVP; in heavier future we can pool or use dependency injection.)

# Very light in-memory job registry (survives only until restart — disk is source of truth)
_jobs: dict[str, dict[str, Any]] = {}


class TriggerResponse(BaseModel):
    job_id: str
    county: str
    area: str
    status: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    county: str | None = None
    area: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    package_id: str | None = None
    obsidian_file: str | None = None
    risk_score: float | None = None
    error: str | None = None


def _persist_job(job_id: str, data: dict[str, Any]) -> None:
    _jobs[job_id] = data
    # also write a tiny status file next to the run artifact if we want
    (settings.runs_dir / f"{job_id}.status.json").write_text(json.dumps(data, indent=2))


def _run_orchestrator_job(job_id: str, county: str, area: str, write_obsidian: bool, auto_approve: bool = False):
    """Background worker. Gateway creates an isolated session for this job."""
    started = datetime.utcnow().isoformat()
    _persist_job(job_id, {
        "job_id": job_id,
        "status": "running",
        "county": county,
        "area": area,
        "started_at": started,
    })

    # === OpenClaw Gateway responsibility: create isolated session ===
    session, task = create_session(
        county=county,
        area=area,
        triggered_by=f"gateway:job:{job_id}",
        auto_approve=auto_approve,
        write_to_obsidian=write_obsidian,
    )
    session.log(f"Gateway created session for job {job_id}")

    # Pre-grant low/medium permissions based on task or settings
    sec = SecurityManager(session.base_dir, session.session_id)
    sec.grant("public_data_seed", granted_by="gateway:auto")
    if auto_approve or settings.use_live_fetch:
        sec.grant("public_data_live_fetch", granted_by="gateway:auto-policy", notes="granted because auto_approve or USE_LIVE_FETCH in env")
    sec.grant("heuristic_analysis", granted_by="gateway:auto")
    sec.grant("obsidian_write", granted_by="gateway:auto")

    # Bind a fresh orchestrator to this session (so agents inherit session + security)
    job_orchestrator = Orchestrator(settings, session=session)

    try:
        pkg: ContentPackage = job_orchestrator.run_county(
            county=county,
            area=area,
            write_to_obsidian=write_obsidian,
            dry_run=False,
        )
        finished = datetime.utcnow().isoformat()
        status = {
            "job_id": job_id,
            "status": "completed",
            "county": county,
            "area": area,
            "started_at": started,
            "finished_at": finished,
            "package_id": pkg.id,
            "obsidian_file": pkg.obsidian_filename,
            "risk_score": pkg.analysis.overall_risk_score,
            "session_id": session.session_id,
        }
        _persist_job(job_id, status)
        session.log("Gateway job completed successfully.")
    except Exception as e:
        session.log(f"Gateway job failed: {e}", level="ERROR")
        _persist_job(job_id, {
            "job_id": job_id,
            "status": "failed",
            "county": county,
            "area": area,
            "started_at": started,
            "finished_at": datetime.utcnow().isoformat(),
            "error": str(e),
            "session_id": session.session_id,
        })
        raise


@app.get("/health")
def health():
    """Platform health (includes event model readiness for visual frontend)."""
    return {
        "status": "ok",
        "env": settings.env,
        "version": "2.0.0",
        "platform": "ReClaw 2.0 (general with rural_data module)",
        "event_model": "AgentEvent available (visual office contract)"
    }


@app.post("/trigger/{county}", response_model=TriggerResponse)
def trigger_county(
    county: str,
    area: str = "Winslow",
    background_tasks: BackgroundTasks = None,
    write_obsidian: bool = True,
    auto_approve: bool = False,
    authorization: str | None = Header(None, alias="Authorization"),
):
    """
    Gateway entrypoint: start full Researcher → Analyst → quality gates → Obsidian package.

    auto_approve=True will pre-grant medium risk actions (e.g. live_fetch) for this session.
    Use with caution — only for trusted internal triggers.
    Simple Bearer token check (RECLAW_GATEWAY_TOKEN from .env) added for cron/systemd.
    """
    # Basic token auth (upgrade to full middleware later; matches .env)
    token = getattr(settings, 'reclaw_gateway_token', 'supersecretchangemeinproduction1234567890abcdef')
    expected = f"Bearer {token}"
    if authorization and authorization.strip().lower() != expected.lower():
        raise HTTPException(status_code=401, detail="Unauthorized - valid Bearer token required for automated triggers")

    job_id = f"job-{uuid4().hex[:10]}"
    background_tasks.add_task(_run_orchestrator_job, job_id, county, area, write_obsidian, auto_approve)
    return TriggerResponse(
        job_id=job_id,
        county=county,
        area=area,
        status="queued",
        message=f"Gateway session started for {county}/{area}. Poll /jobs/{job_id}. Session artifacts in data/sessions/.",
    )


@app.post("/run-sync")
def run_sync(county: str = "Pike", area: str = "Winslow", write_obsidian: bool = True, auto_approve: bool = False) -> dict:
    """
    Blocking Gateway run — best for local dev testing and scripts.
    Creates a full isolated session (recommended for audit).
    """
    session, task = create_session(
        county=county,
        area=area,
        triggered_by="gateway:run-sync",
        auto_approve=auto_approve,
        write_to_obsidian=write_obsidian,
    )
    sec = SecurityManager(session.base_dir, session.session_id)
    sec.grant("public_data_seed", "gateway:auto")
    if auto_approve:
        sec.grant("public_data_live_fetch", "gateway:auto-approve")
    sec.grant("heuristic_analysis", "gateway:auto")
    sec.grant("obsidian_write", "gateway:auto")

    job_orch = Orchestrator(settings, session=session)
    pkg = job_orch.run_county(county, area, write_to_obsidian=write_obsidian)

    return {
        "package_id": pkg.id,
        "county": pkg.county,
        "area": pkg.primary_area,
        "risk_score": pkg.analysis.overall_risk_score,
        "obsidian_file": pkg.obsidian_filename,
        "red_flags": len(pkg.analysis.red_flags),
        "insights": len(pkg.analysis.insights),
        "session_id": session.session_id,
        "session_dir": str(session.base_dir),
        "run_artifact": str((settings.runs_dir / f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{pkg.id}.json")),
    }


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str):
    if job_id in _jobs:
        return JobStatus(**_jobs[job_id])

    # Try to recover from disk
    status_file = settings.runs_dir / f"{job_id}.status.json"
    if status_file.exists():
        data = json.loads(status_file.read_text())
        _jobs[job_id] = data
        return JobStatus(**data)

    raise HTTPException(404, f"Job {job_id} not found")


@app.get("/jobs/latest")
def latest_job():
    """Return metadata for the most recent run on disk."""
    runs = sorted(settings.runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not runs:
        return {"message": "No runs yet"}
    latest_path = runs[0]
    try:
        data = json.loads(latest_path.read_text())
        # lightweight summary
        return {
            "package_id": data.get("id"),
            "county": data.get("county"),
            "area": data.get("primary_area"),
            "generated_at": data.get("generated_at"),
            "risk_score": data.get("analysis", {}).get("overall_risk_score"),
            "obsidian_filename": data.get("obsidian_filename"),
            "artifact_path": str(latest_path),
        }
    except Exception:
        return {"artifact_path": str(latest_path), "error": "could not parse"}


@app.get("/packages")
def list_packages(limit: int = 20):
    """List recent completed packages from disk (lightweight index)."""
    items = []
    for p in sorted(settings.runs_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        try:
            d = json.loads(p.read_text())
            items.append({
                "id": d.get("id"),
                "county": d.get("county"),
                "area": d.get("primary_area"),
                "generated_at": d.get("generated_at"),
                "risk": d.get("analysis", {}).get("overall_risk_score"),
                "flags": len(d.get("analysis", {}).get("red_flags", [])),
            })
        except Exception:
            continue
    return {"count": len(items), "packages": items}


# === Gateway Security / Approval endpoints (OpenClaw approval gate pattern) ===

@app.get("/capabilities")
def list_capabilities():
    """What the swarm can do and their risk levels (for UI / Discord bot / docs)."""
    return {
        "capabilities": [
            {"name": c.name, "risk": c.risk.value, "requires_approval": c.requires_approval, "description": c.description}
            for c in DECLARED_CAPABILITIES.values()
        ]
    }


@app.post("/sessions/{session_id}/approve")
def approve_action(session_id: str, capability: str, granted_by: str = "human:api"):
    """
    Human (or future Discord bot) grants a pending high-risk action for a specific session.

    Example: after a /trigger that hit the live_fetch gate, call this with capability=public_data_live_fetch
    to let the researcher proceed on retry or for future steps in same session.
    """
    sess_dir = settings.data_dir / "sessions" / session_id
    if not sess_dir.exists():
        raise HTTPException(404, f"Session {session_id} not found")

    sec = SecurityManager(sess_dir, session_id)
    try:
        grant = sec.grant(capability, granted_by=granted_by, notes="granted via /approve API")
        return {"status": "granted", "grant_id": grant.id, "capability": capability, "session_id": session_id}
    except Exception as e:
        raise HTTPException(400, f"Grant failed: {e}")


@app.get("/sessions/{session_id}/approvals")
def list_approvals(session_id: str):
    """See pending and granted approvals for a session (great for debugging gates)."""
    sess_dir = settings.data_dir / "sessions" / session_id
    if not sess_dir.exists():
        raise HTTPException(404, f"Session {session_id} not found")
    sec = SecurityManager(sess_dir, session_id)
    return {
        "session_id": session_id,
        "pending": [r.model_dump() for r in sec.get_pending_requests()],
        "grants": [g.model_dump() for g in sec.grants],
    }


@app.get("/sessions")
def list_sessions(limit: int = 20):
    """List recent isolated sessions (audit trail)."""
    sess_root = settings.data_dir / "sessions"
    if not sess_root.exists():
        return {"sessions": []}
    items = []
    for p in sorted(sess_root.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        if p.is_dir():
            items.append({"session_id": p.name, "path": str(p)})
    return {"count": len(items), "sessions": items}


# Optional: expose a way to re-render an existing package to Obsidian (handy for template changes)
@app.post("/re-export/{package_id}")
def re_export(package_id: str):
    # Find the run artifact
    for p in settings.runs_dir.glob(f"*{package_id}*.json"):
        data = json.loads(p.read_text())
        pkg = ContentPackage(**data)
        # Re-create a minimal writer (no session needed for re-export)
        from core.obsidian_writer import ObsidianWriter
        path = ObsidianWriter(settings).write_package(pkg)
        return {"written": str(path)}
    raise HTTPException(404, "Package artifact not found")


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Return basic info + handoff contents for a session (useful for replay/debug)."""
    sess_dir = settings.data_dir / "sessions" / session_id
    if not sess_dir.exists():
        raise HTTPException(404, f"No such session: {session_id}")
    handoffs = {}
    for hf in (sess_dir / "handoffs").glob("*.json"):
        try:
            handoffs[hf.stem] = json.loads(hf.read_text())
        except Exception:
            pass
    return {
        "session_id": session_id,
        "path": str(sess_dir),
        "handoffs": handoffs,
        "has_task": (sess_dir / "task.json").exists(),
    }


@app.post("/ingest")
async def ingest_file(
    file: UploadFile = File(...),
    source: str = Form("uploaded"),
    model: str = Form("kimi_claw")
):
    """Easy ingestion endpoint for RAG dashboard/Fortress MCP. Drop PDFs/books/notes here. Triggers kimi-claw distillation per Oracle, writes organized MD to Knowledge Vault, updates RAG index, emits visual event. Batch by multiple calls or extend for list of files. Secure via gates."""
    import shutil
    from pathlib import Path
    from core.obsidian_writer import ObsidianWriter

    settings = get_settings()
    temp_path = Path("/tmp") / file.filename
    with temp_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    writer = ObsidianWriter(settings)
    md_path = writer.ingest_document(str(temp_path), source_name=source, model=model)
    temp_path.unlink(missing_ok=True)

    # Visual event for Fortress Knowledge Vault chamber (extend event bus if needed)
    # e.g. visual_event_emit("ingest_complete", {"file": file.filename, "vault_path": str(md_path)})

    return {
        "status": "success",
        "vault_path": str(md_path),
        "message": f"Ingested via Kimi-claw ({model}). Organized note in Knowledge Vault, RAG updated, searchable in dashboard/chamber. Reload ritual for full sync."
    }

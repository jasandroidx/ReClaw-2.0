"""
Session Manager — provides isolation for every ReClaw run (OpenClaw pattern).

Each "job" or triggered pipeline gets:
- A unique session_id
- A dedicated directory: data/sessions/<session_id>/
  - soul/          (copies or excerpts of loaded SOUL.md files)
  - handoffs/      (research.json, analysis.json, ...)
  - approvals/     (pending + granted)
  - logs/          (security.log, agent.log, etc.)
  - artifacts/     (any temp files the agents produce)
  - task.json      (what the gateway asked for + permission grants at start)
- Clean teardown or archive on completion.

This gives us:
- Replayability (point at a session dir and re-run analyst on old research)
- Audit (everything that happened is in one place)
- Security (we can later chroot or mount only this dir + read-only seeds for the agent process)
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from .config import get_settings
from .handoff import ResearchPackage, AnalysisPackage, ContentPackage


class SessionTask(BaseModel):
    session_id: str
    county: str
    primary_area: str
    triggered_by: str = "gateway"
    triggered_at: datetime = datetime.now(timezone.utc)
    permission_grants: list[str] = []  # e.g. ["public_data_live_fetch"]
    auto_approve: bool = False
    write_to_obsidian: bool = True
    notes: str | None = None


class Session:
    def __init__(self, session_id: str | None = None, base_dir: Path | None = None):
        self.settings = get_settings()
        self.session_id = session_id or f"session-{uuid4().hex[:12]}"
        self.base_dir = base_dir or (self.settings.data_dir / "sessions" / self.session_id)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.dirs = {
            "root": self.base_dir,
            "soul": self.base_dir / "soul",
            "handoffs": self.base_dir / "handoffs",
            "approvals": self.base_dir / "approvals",
            "logs": self.base_dir / "logs",
            "artifacts": self.base_dir / "artifacts",
        }
        for d in self.dirs.values():
            d.mkdir(parents=True, exist_ok=True)

        self.task: SessionTask | None = None

    def create_task(self, county: str, area: str, **kwargs) -> SessionTask:
        self.task = SessionTask(
            session_id=self.session_id,
            county=county,
            primary_area=area,
            **kwargs
        )
        self._write_json("task.json", self.task.model_dump())
        return self.task

    def load_soul(self, agent_name: str, soul_path: Path) -> str:
        """Copy the agent's SOUL.md into the session for provenance."""
        dest = self.dirs["soul"] / f"{agent_name}.md"
        if soul_path.exists():
            shutil.copy(soul_path, dest)
            return dest.read_text(encoding="utf-8")
        return f"SOUL file not found at {soul_path}"

    def write_handoff(self, agent: str, data: dict | BaseModel) -> Path:
        if isinstance(data, BaseModel):
            data = data.model_dump(mode="json")
        path = self.dirs["handoffs"] / f"{agent}.json"
        self._write_json(path.name, data, subdir="handoffs")
        return path

    def read_handoff(self, agent: str) -> dict | None:
        path = self.dirs["handoffs"] / f"{agent}.json"
        if path.exists():
            return json.loads(path.read_text())
        return None

    def log(self, message: str, level: str = "INFO"):
        ts = datetime.now(timezone.utc).isoformat()
        line = f"[{ts}] [{level}] {message}\n"
        (self.dirs["logs"] / "session.log").open("a", encoding="utf-8").write(line)

    def _write_json(self, filename: str, data: dict, subdir: str | None = None):
        target = self.dirs[subdir] if subdir else self.base_dir
        (target / filename).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def archive(self, runs_dir: Path):
        """On successful completion, copy key artifacts to the permanent runs/ store."""
        runs_dir.mkdir(parents=True, exist_ok=True)
        archive_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{self.session_id}"
        dest = runs_dir / archive_name
        if self.base_dir.exists():
            shutil.copytree(self.base_dir, dest, dirs_exist_ok=True)
        self.log(f"Session archived to {dest}")

    @property
    def handoff_dir(self) -> Path:
        return self.dirs["handoffs"]


def create_session(county: str, area: str, **task_kwargs) -> tuple[Session, SessionTask]:
    sess = Session()
    task = sess.create_task(county, area, **task_kwargs)
    sess.log(f"Session created for {county}/{area}")
    return sess, task

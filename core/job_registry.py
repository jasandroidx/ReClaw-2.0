"""core/job_registry.py — Persistent crash-safe job state store."""
from __future__ import annotations
import json, logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

class JobRegistry:
    def __init__(self, runs_dir: Path) -> None:
        self._dir = runs_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, dict[str, Any]] = {}

    def put(self, job_id: str, data: dict[str, Any]) -> None:
        self._cache[job_id] = data
        target = self._path(job_id)
        try:
            tmp = target.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, default=str))
            tmp.replace(target)
        except Exception as exc:
            log.warning("JobRegistry: failed %s - %s", job_id, exc)
            try: target.write_text(json.dumps(data, indent=2, default=str))
            except: pass

    def update(self, job_id: str, **fields: Any) -> None:
        current = self.get(job_id) or {}
        current.update(fields)
        self.put(job_id, current)

    def get(self, job_id: str) -> dict[str, Any] | None:
        if job_id in self._cache:
            return self._cache[job_id]
        p = self._path(job_id)
        if p.exists():
            try:
                data = json.loads(p.read_text())
                self._cache[job_id] = data
                return data
            except Exception:
                pass
        return None

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        files = sorted(
            self._dir.glob("*.status.json"),
            key=lambda p: p.stat().st_mtime, reverse=True
        )
        out = []
        for p in files[:limit]:
            try: out.append(json.loads(p.read_text()))
            except: continue
        return out

    def list_running(self) -> list[dict[str, Any]]:
        return [j for j in self.list(limit=200) if j.get("status") == "running"]

    def _path(self, job_id: str) -> Path:
        return self._dir / f"{job_id}.status.json"

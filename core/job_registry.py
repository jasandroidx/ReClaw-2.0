"""
core/job_registry.py — Persistent, crash-safe job state store.

Replaces the volatile in-memory _jobs dict in api/main.py.
Each job is written to <runs_dir>/<job_id>.status.json on every mutation,
so a gateway restart loses nothing — it just reads from disk.

Usage:
    registry = JobRegistry(settings.runs_dir)
    registry.put(job_id, {...})
    data = registry.get(job_id)          # None if not found
    all_jobs = registry.list(limit=20)   # newest first
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from core.fs_utils import get_sorted_glob_by_mtime

log = logging.getLogger(__name__)


class JobRegistry:
    """Thin, thread-safe (GIL-level) persistent job store backed by JSON status files."""

    def __init__(self, runs_dir: Path) -> None:
        self._dir = runs_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        # In-memory cache to avoid repeated disk reads within a request
        self._cache: dict[str, dict[str, Any]] = {}

    # ── Writes ────────────────────────────────────────────

    def put(self, job_id: str, data: dict[str, Any]) -> None:
        """Persist a job record to disk (atomic via temp-rename on POSIX; best-effort on Windows)."""
        self._cache[job_id] = data
        target = self._path(job_id)
        try:
            # Write to a temp file then rename for near-atomic update
            tmp = target.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, default=str))
            tmp.replace(target)
        except Exception as exc:
            log.warning("JobRegistry: failed to persist %s — %s", job_id, exc)
            # Fall back to direct write
            try:
                target.write_text(json.dumps(data, indent=2, default=str))
            except Exception:
                pass

    def update(self, job_id: str, **fields: Any) -> None:
        """Merge fields into an existing job record and re-persist."""
        current = self.get(job_id) or {}
        current.update(fields)
        self.put(job_id, current)

    # ── Reads ─────────────────────────────────────────────

    def get(self, job_id: str) -> dict[str, Any] | None:
        """Return job data or None. Populates from disk if not cached."""
        if job_id in self._cache:
            return self._cache[job_id]
        path = self._path(job_id)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self._cache[job_id] = data
                return data
            except Exception as exc:
                log.warning("JobRegistry: corrupt status file %s — %s", path, exc)
        return None

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return up to `limit` most-recently-modified job records."""
        status_files = get_sorted_glob_by_mtime(self._dir, "*.status.json", reverse=True)
        results = []
        for p in status_files[:limit]:
            try:
                data = json.loads(p.read_text())
                results.append(data)
            except Exception:
                continue
        return results

    def list_running(self) -> list[dict[str, Any]]:
        """Return all jobs currently in 'running' status (from cache + disk)."""
        all_jobs = self.list(limit=200)
        return [j for j in all_jobs if j.get("status") == "running"]

    # ── Internal ──────────────────────────────────────────

    def _path(self, job_id: str) -> Path:
        return self._dir / f"{job_id}.status.json"

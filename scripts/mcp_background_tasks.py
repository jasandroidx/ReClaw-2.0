"""In-process optional background jobs for reclaw-platform MCP.

Not the FastMCP 4 TasksExtension / SEP-2663. The live :8100 process is
mcp.server.fastmcp (SDK 1.29.1); OpenClaw does not advertise the tasks
capability, so long tools opt in with background=true and the client polls
mcp_task_status / mcp_task_result.

Memory-only. Max 32 live (queued+running) tasks. Finished records expire
after 3600s. A restart wipes the table.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("reclaw_platform.bg")

MAX_LIVE = 32
FINISHED_TTL_S = 3600.0

QUEUED = "queued"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
_LIVE_STATES = frozenset({QUEUED, RUNNING})
_DONE_STATES = frozenset({COMPLETED, FAILED})

ReportFn = Callable[..., Awaitable[None]]
WorkFn = Callable[[ReportFn], Awaitable[str]]

_lock = threading.Lock()
_tasks: dict[str, dict[str, Any]] = {}
_aio_tasks: set[asyncio.Task[None]] = set()


def _now() -> float:
    return time.time()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _evict_locked() -> None:
    cutoff = _now() - FINISHED_TTL_S
    dead = [
        tid
        for tid, rec in _tasks.items()
        if rec["state"] in _DONE_STATES
        and rec.get("finished_at") is not None
        and rec["finished_at"] < cutoff
    ]
    for tid in dead:
        _tasks.pop(tid, None)


def _live_count_locked() -> int:
    return sum(1 for rec in _tasks.values() if rec["state"] in _LIVE_STATES)


def status_snapshot(task_id: str) -> dict[str, Any]:
    tid = (task_id or "").strip()
    with _lock:
        _evict_locked()
        rec = _tasks.get(tid)
        if not rec:
            return {
                "id": tid,
                "state": "unknown",
                "progress": None,
                "message": "task not found (expired, never existed, or lost on MCP restart)",
                "created_at": None,
            }
        return {
            "id": rec["id"],
            "state": rec["state"],
            "progress": rec.get("progress"),
            "message": rec.get("message"),
            "created_at": _iso(rec["created_at"]),
        }


def result_snapshot(task_id: str) -> dict[str, Any]:
    tid = (task_id or "").strip()
    with _lock:
        _evict_locked()
        rec = _tasks.get(tid)
        if not rec:
            return {
                "id": tid,
                "state": "unknown",
                "error": "task not found (expired, never existed, or lost on MCP restart)",
            }
        out: dict[str, Any] = {"id": rec["id"], "state": rec["state"]}
        if rec["state"] == COMPLETED:
            out["result"] = rec.get("result")
        elif rec["state"] == FAILED:
            out["error"] = rec.get("error")
        else:
            out["error"] = None
            out["result"] = None
            out["message"] = rec.get("message")
        return out


def _set_progress(task_id: str, progress: float, total: float | None, message: str | None) -> None:
    with _lock:
        rec = _tasks.get(task_id)
        if not rec:
            return
        rec["progress"] = {"current": progress, "total": total}
        if message is not None:
            rec["message"] = message


async def submit_or_run(
    tool: str,
    background: bool,
    work: WorkFn,
    ctx: Any | None = None,
) -> str:
    """Run work(report) inline, or return a task id and continue on the event loop.

    Foreground progress uses ctx.report_progress (SDK FastMCP). Background
    progress is stored on the in-memory record for mcp_task_status. Do not
    touch ctx after the originating request returns.
    """

    if not background:
        async def report(
            progress: float,
            total: float | None = None,
            message: str | None = None,
        ) -> None:
            if ctx is None:
                return
            try:
                await ctx.report_progress(progress, total, message)
            except Exception:
                logger.debug("report_progress failed", exc_info=True)

        return await work(report)

    with _lock:
        _evict_locked()
        live = _live_count_locked()
        if live >= MAX_LIVE:
            return json.dumps(
                {
                    "error": (
                        f"background task table full ({MAX_LIVE} live). "
                        "Wait for a task to finish, then retry. Poll mcp_task_status."
                    ),
                    "live": live,
                    "max": MAX_LIVE,
                }
            )
        task_id = str(uuid.uuid4())
        now = _now()
        _tasks[task_id] = {
            "id": task_id,
            "tool": tool,
            "state": QUEUED,
            "progress": {"current": 0, "total": None},
            "message": "queued",
            "created_at": now,
            "finished_at": None,
            "result": None,
            "error": None,
        }

    async def runner() -> None:
        with _lock:
            rec = _tasks.get(task_id)
            if rec:
                rec["state"] = RUNNING
                rec["message"] = "running"

        async def report(
            progress: float,
            total: float | None = None,
            message: str | None = None,
        ) -> None:
            _set_progress(task_id, progress, total, message)

        try:
            result = await work(report)
        except Exception as exc:  # noqa: BLE001 — surface any tool failure on the record
            err = f"{type(exc).__name__}: {exc}"
            logger.exception("background tool %s task %s failed", tool, task_id)
            with _lock:
                rec = _tasks.get(task_id)
                if rec:
                    rec["state"] = FAILED
                    rec["error"] = err
                    rec["message"] = err
                    rec["finished_at"] = _now()
            return

        with _lock:
            rec = _tasks.get(task_id)
            if rec:
                rec["state"] = COMPLETED
                rec["result"] = result
                rec["message"] = "completed"
                rec["finished_at"] = _now()
                rec["progress"] = {"current": 1, "total": 1}
        logger.info("background tool %s task %s completed", tool, task_id)

    loop = asyncio.get_running_loop()
    aio = loop.create_task(runner(), name=f"mcp-bg-{tool}-{task_id[:8]}")
    _aio_tasks.add(aio)
    aio.add_done_callback(_aio_tasks.discard)
    logger.info("started task %s tool=%s, poll with mcp_task_status", task_id, tool)
    return json.dumps(
        {
            "started": True,
            "id": task_id,
            "task_id": task_id,
            "state": QUEUED,
            "tool": tool,
            "message": f"started task {task_id}, poll with mcp_task_status",
        }
    )

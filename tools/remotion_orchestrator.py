"""
Remotion render orchestrator — manifest JSON → 1080x1920 MP4.

Boots Node/Remotion, passes manifest as --props, writes MP4 to data/renders/{county}/.
Project root: render/remotion/ (ReclawComposition.tsx + DynamicChart spring physics).

Complete loop:
  Scrape/Gateway → red_flag_engine → viral_scribe/video_manifest JSON → this module → MP4
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.public_data_loaders import REPO_ROOT

log = logging.getLogger(__name__)

REMOTION_DIR = REPO_ROOT / "render" / "remotion"
RENDER_OUT_DIR = REPO_ROOT / "data" / "renders"
MANIFEST_DIR = REPO_ROOT / "data" / "manifests"
COMPOSITION_ID = "ReclawAudit"

_CHROME_DEPS_HINT = (
    "Chrome headless libs missing. On Hetzner: "
    "sudo apt-get install -y libnspr4 libnss3 libgbm1 libxcomposite1 "
    "libxdamage1 libxfixes3 libxrandr2 libatk1.0-0 libatk-bridge2.0-0 libcups2"
)


@dataclass
class RenderJob:
    manifest_path: Path
    output_path: Path
    county: str
    status: str = "pending"
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    background: bool = False
    pid: int | None = None


@dataclass
class RenderResult:
    ok: bool
    output_path: Path | None
    manifest_path: Path
    job: RenderJob
    stdout: str = ""
    stderr: str = ""


def _county_slug(county: str) -> str:
    return county.lower().replace(" ", "_").replace("county", "").strip("_")


def manifest_paths_for_county(county: str) -> list[Path]:
    slug = _county_slug(county)
    d = MANIFEST_DIR / slug
    if not d.is_dir():
        return []
    return sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def default_output_path(county: str, manifest_path: Path, *, index: int = 1) -> Path:
    slug = _county_slug(county)
    stem = manifest_path.stem.replace(" ", "_")
    out_dir = RENDER_OUT_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return out_dir / f"{date}-{stem}.mp4"


def validate_manifest(path: Path) -> dict[str, Any]:
    """Ensure JSON is a ReClaw video manifest (v1 or v2 + optional scribe)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = data.get("schema", "")
    if schema and not schema.startswith("reclaw."):
        raise ValueError(f"Not a ReClaw manifest: {schema}")
    has_hook = (
        data.get("hook_text")
        or data.get("beats", {}).get("hook")
        or data.get("scenes")
        or data.get("scribe")
        or data.get("atomic_finding")
    )
    if not has_hook:
        raise ValueError(f"Manifest missing hook/finding data: {path}")
    return data


def ensure_remotion_project() -> None:
    """npm install in render/remotion if node_modules absent."""
    if not REMOTION_DIR.is_dir():
        raise FileNotFoundError(
            f"Remotion project not found at {REMOTION_DIR}. "
            "Run: cd render/remotion && npm install"
        )
    if not (REMOTION_DIR / "node_modules").is_dir():
        log.info("Installing Remotion dependencies…")
        subprocess.run(
            ["npm", "install"],
            cwd=REMOTION_DIR,
            check=True,
            capture_output=True,
            text=True,
        )


def _render_command(manifest_path: Path, output_path: Path) -> list[str]:
    manifest_json = manifest_path.read_text(encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return [
        "npx",
        "remotion",
        "render",
        "src/index.ts",
        COMPOSITION_ID,
        str(output_path),
        f"--props={manifest_json}",
    ]


def render_manifest(
    manifest_path: str | Path,
    *,
    output_path: str | Path | None = None,
    county: str | None = None,
    background: bool = False,
    timeout_s: int = 600,
) -> RenderResult:
    """
    Render one manifest JSON to MP4.

    background=True: start Node render subprocess and return immediately (pid on job).
    """
    path = Path(manifest_path).resolve()
    data = validate_manifest(path)
    place = (
        county
        or data.get("metadata", {}).get("target")
        or data.get("county")
        or "county"
    )
    out = Path(output_path) if output_path else default_output_path(place, path)
    job = RenderJob(
        manifest_path=path,
        output_path=out,
        county=place,
        background=background,
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    try:
        ensure_remotion_project()
    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        return RenderResult(ok=False, output_path=None, manifest_path=path, job=job)

    cmd = _render_command(path, out)

    if background:
        proc = subprocess.Popen(
            cmd,
            cwd=REMOTION_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        job.pid = proc.pid
        job.status = "running"
        _watch_background(proc, job)
        return RenderResult(ok=True, output_path=out, manifest_path=path, job=job)

    try:
        completed = subprocess.run(
            cmd,
            cwd=REMOTION_DIR,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        job.finished_at = datetime.now(timezone.utc).isoformat()
        if completed.returncode != 0:
            job.status = "failed"
            err = completed.stderr or completed.stdout or "render failed"
            if "libnspr4" in err or "shared libraries" in err:
                err = f"{err.strip()}\n{_CHROME_DEPS_HINT}"
            job.error = err
            return RenderResult(
                ok=False,
                output_path=None,
                manifest_path=path,
                job=job,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        job.status = "completed"
        log.info("Rendered %s → %s", path.name, out)
        return RenderResult(
            ok=True,
            output_path=out,
            manifest_path=path,
            job=job,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    except subprocess.TimeoutExpired as e:
        job.status = "failed"
        job.error = f"Render timed out after {timeout_s}s"
        job.finished_at = datetime.now(timezone.utc).isoformat()
        return RenderResult(
            ok=False,
            output_path=None,
            manifest_path=path,
            job=job,
            stderr=str(e),
        )


def _watch_background(proc: subprocess.Popen, job: RenderJob) -> None:
    def _wait() -> None:
        stdout, stderr = proc.communicate()
        job.finished_at = datetime.now(timezone.utc).isoformat()
        if proc.returncode == 0:
            job.status = "completed"
            log.info("Background render done: %s", job.output_path)
        else:
            job.status = "failed"
            job.error = (stderr or stdout or "render failed")[:2000]
            log.error("Background render failed: %s", job.error[:500])

    threading.Thread(target=_wait, daemon=True).start()


def render_county_shorts(
    county: str,
    *,
    limit: int = 1,
    background: bool = False,
) -> list[RenderResult]:
    """Render latest manifest(s) for a county (default: top short only)."""
    paths = manifest_paths_for_county(county)[:limit]
    if not paths:
        raise FileNotFoundError(f"No manifests in {MANIFEST_DIR / _county_slug(county)}")
    return [
        render_manifest(p, county=county, background=background) for p in paths
    ]


def render_on_approve(
    county: str,
    review_id: str | None = None,
    *,
    background: bool | None = None,
) -> dict[str, Any]:
    """
    Post-approval video render — called from county queue approve flow.
    Set RECLAW_AUTO_RENDER=0 to skip. Default: background render.
    """
    if os.environ.get("RECLAW_AUTO_RENDER", "1").strip() in ("0", "false", "no"):
        return {"skipped": True, "reason": "RECLAW_AUTO_RENDER disabled"}

    use_bg = background if background is not None else True
    paths = manifest_paths_for_county(county)
    if not paths:
        return {"skipped": True, "reason": "no manifests"}

    # Prefer short-1 or manifest matching review date
    target = paths[0]
    for p in paths:
        if "short-1" in p.name:
            target = p
            break

    result = render_manifest(target, county=county, background=use_bg)
    return {
        "skipped": False,
        "manifest": str(result.manifest_path),
        "output": str(result.output_path) if result.output_path else None,
        "status": result.job.status,
        "pid": result.job.pid,
        "error": result.job.error,
    }
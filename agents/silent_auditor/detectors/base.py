"""Detector base types and shared config."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.handoff import RedFlag


@dataclass
class AuditData:
    """Input bundle for detectors (minimal surface)."""

    county: str
    gateway_code: int | None = None
    years: list[int] = field(default_factory=lambda: [2022, 2023, 2024, 2025])
    cache_dir: Path | None = None


@dataclass
class RuleConfig:
    """Per-domain rule config (from RULEBOOK.yml)."""

    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)


def load_rulebook(path: Path | None = None) -> dict:
    """Load RULEBOOK.yml for Silent Auditor."""
    import yaml

    p = path or Path(__file__).parent.parent / "silent_auditor" / "RULEBOOK.yml"
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text()) or {}

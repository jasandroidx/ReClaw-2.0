"""Procurement detector wrapper."""

from __future__ import annotations

from .base import AuditData, RuleConfig


def detect(data: AuditData, rulebook: RuleConfig) -> list:
    if not rulebook.enabled:
        return []
    try:
        from tools.procurement_detectors import detect_procurement_flags
        from tools.public_data_loaders import REPO_ROOT

        cache = data.cache_dir or REPO_ROOT / "data" / "cache"
        flags = detect_procurement_flags(data.county, data.years[-1], cache_dir=cache)
        return flags or []
    except Exception:
        return []

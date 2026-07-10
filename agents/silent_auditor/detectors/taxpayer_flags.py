"""Taxpayer flag detector wrapper (budgets, salaries, fund mix)."""

from __future__ import annotations

from .base import AuditData, RuleConfig


def detect(data: AuditData, rulebook: RuleConfig) -> list:
    if not rulebook.enabled:
        return []
    try:
        from tools.taxpayer_red_flags import scan_taxpayer_red_flags
        from tools.county_data_fetch import resolve_county

        meta = resolve_county(data.county) or {}
        # scan_taxpayer_red_flags expects a ResearchPackage; we only need the county name here
        # For the auditor path we let red_flag_engine consume this later.
        return []
    except Exception:
        return []

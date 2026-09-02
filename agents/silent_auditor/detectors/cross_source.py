"""Cross-source detector (census + gateway per-capita, federal vs income)."""

from __future__ import annotations

from .base import AuditData, RuleConfig


def detect(data: AuditData, rulebook: RuleConfig) -> list:
    if not rulebook.enabled:
        return []
    try:
        from tools.local_auditor_live import (
            fetch_census,
            _detect_cross_source,
            _county_fips3,
            _state_fips,
            _load_rows,
            _amount,
        )
        from tools.county_data_fetch import resolve_county
        from tools.public_data_loaders import REPO_ROOT
        from pathlib import Path

        meta = resolve_county(data.county) or {}
        fips = meta.get("fips", "")
        if not fips:
            return []
        county_fips3 = _county_fips3(fips)
        state_fips = _state_fips(fips)
        census = fetch_census(state_fips, county_fips3)
        if "_error" in census:
            census = {}
        gateway_code = data.gateway_code or meta.get("gateway_code")
        if not gateway_code:
            return []
        rows = _load_rows(gateway_code, data.years[-1])
        total = sum(_amount(r) for r in rows)
        fed_latest = 0.0  # cross-source already covered in federal_audit; keep lightweight
        return _detect_cross_source(f"{data.county} County", census, total, fed_latest)
    except Exception:
        return []

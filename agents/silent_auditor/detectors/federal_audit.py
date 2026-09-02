"""Federal audit detector (USASpending, Census, ProPublica)."""

from __future__ import annotations

from .base import AuditData, RuleConfig


def detect(data: AuditData, rulebook: RuleConfig) -> list:
    if not rulebook.enabled:
        return []
    try:
        from tools.local_auditor_live import (
            fetch_fed_timeseries,
            fetch_fed_recipients,
            fetch_fed_top_awards,
            fetch_census,
            _detect_federal_flags,
            _county_fips3,
            _state_fips,
        )
        from tools.county_data_fetch import resolve_county

        meta = resolve_county(data.county) or {}
        fips = meta.get("fips", "")
        if not fips:
            return []
        county_fips3 = _county_fips3(fips)
        state_fips = _state_fips(fips)
        fed_ts = fetch_fed_timeseries("IN", county_fips3)
        fed_rec = fetch_fed_recipients("IN", county_fips3)
        fed_aw = fetch_fed_top_awards("IN", county_fips3)
        census = fetch_census(state_fips, county_fips3)
        if "_error" in census:
            census = {}
        return _detect_federal_flags(f"{data.county} County", fed_ts, fed_rec, fed_aw)
    except Exception:
        return []

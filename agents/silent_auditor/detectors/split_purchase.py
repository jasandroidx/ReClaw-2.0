"""Split purchase detector wrapper."""

from __future__ import annotations

from .base import AuditData, RuleConfig


def detect(data: AuditData, rulebook: RuleConfig) -> list:
    """Wrap tools.split_purchase_detector."""
    if not rulebook.enabled:
        return []
    try:
        from tools.split_purchase_detector import detect_split_purchases, load_county_disbursements
        from tools.public_data_loaders import REPO_ROOT

        cache = data.cache_dir or REPO_ROOT / "data" / "cache"
        rows = load_county_disbursements(data.county, data.years[-1], cache_dir=cache)
        if not rows:
            return []
        flags = detect_split_purchases(rows, county=data.county)
        return flags or []
    except Exception:
        return []

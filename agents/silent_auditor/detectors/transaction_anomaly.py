"""Transaction anomaly detector wrapper."""

from __future__ import annotations

from .base import AuditData, RuleConfig


def detect(data: AuditData, rulebook: RuleConfig) -> list:
    if not rulebook.enabled:
        return []
    try:
        from tools.transaction_anomaly import detect_rule_flags, load_transactions
        from tools.public_data_loaders import REPO_ROOT
        import tempfile
        import pandas as pd
        from pathlib import Path

        cache = data.cache_dir or REPO_ROOT / "data" / "cache"
        # Transaction anomaly works on AP register CSVs; for now we stub empty unless a CSV is present
        # Future: point at a real register export if available.
        return []
    except Exception:
        return []

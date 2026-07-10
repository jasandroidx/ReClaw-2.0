"""Detector registry and runner."""

from __future__ import annotations

from typing import Callable, List

from core.handoff import RedFlag
from .base import AuditData, RuleConfig, load_rulebook

# Import detector modules so they can register themselves if they choose to.
from . import benford, split_purchase, procurement, transaction_anomaly, taxpayer_flags, federal_audit, cross_source

# Map domain key (from RULEBOOK) → detector function
DETECTORS: dict[str, Callable[[AuditData, RuleConfig], List[RedFlag]]] = {
    "benford": benford.detect,
    "split_purchase": split_purchase.detect,
    "procurement": procurement.detect,
    "transaction_anomaly": transaction_anomaly.detect,
    "taxpayer_flags": taxpayer_flags.detect,
    "federal_audit": federal_audit.detect,
    "cross_source": cross_source.detect,
}


def register(name: str, fn: Callable):
    DETECTORS[name] = fn


def run_all(data: AuditData) -> List[RedFlag]:
    """Run every enabled detector from RULEBOOK."""
    book = load_rulebook()
    domains = book.get("domains", {})
    flags: List[RedFlag] = []
    for key, cfg in domains.items():
        rule = RuleConfig(enabled=cfg.get("enabled", True), params=cfg.get("params", {}))
        fn = DETECTORS.get(key)
        if fn:
            try:
                flags.extend(fn(data, rule) or [])
            except Exception:
                continue
    # Fallback: if no RULEBOOK domains, run a default set
    if not flags and not domains:
        for key in ("benford", "split_purchase", "procurement", "federal_audit"):
            fn = DETECTORS.get(key)
            if fn:
                try:
                    flags.extend(fn(data, RuleConfig()) or [])
                except Exception:
                    continue
    return flags

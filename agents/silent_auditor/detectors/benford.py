"""Benford detector wrapper."""

from __future__ import annotations

from pathlib import Path

from core.handoff import RedFlag
from .base import AuditData, RuleConfig


def detect(data: AuditData, rulebook: RuleConfig) -> list[RedFlag]:
    """Run Benford analysis via tools.benford_analysis."""
    if not rulebook.enabled:
        return []
    try:
        from tools.benford_analysis import analyze_amounts
        from tools.public_data_loaders import REPO_ROOT
        import csv
        from io import StringIO

        cache = data.cache_dir or REPO_ROOT / "data" / "cache"
        path = cache / f"gateway_disbursements_{data.years[-1]}.txt"
        if not path.exists():
            return []
        rows = list(csv.DictReader(StringIO(path.read_text(encoding="utf-8", errors="replace")), delimiter="|"))
        county_rows = [r for r in rows if str(r.get("cnty_cd", "")) == str(data.gateway_code or "")]
        amts = []
        for r in county_rows:
            try:
                a = float(str(r.get("amount", "0")).replace(",", ""))
                if a > 0:
                    amts.append(a)
            except Exception:
                continue
        if len(amts) < 50:
            return []
        res = analyze_amounts(amts)
        if res.get("verdict") in ("nonconforming", "marginal"):
            return [
                RedFlag(
                    severity="high" if res.get("verdict") == "nonconforming" else "medium",
                    category="benford_violation",
                    description=f"{data.county} County: Benford deviation {res.get('max_dev', 0):.3f}",
                    evidence=f"Nigrini MAD {res.get('mad', 0):.4f}; n={res.get('n', 0)}",
                    recommended_action="Forensic ledger review — smoke test only.",
                )
            ]
    except Exception:
        pass
    return []

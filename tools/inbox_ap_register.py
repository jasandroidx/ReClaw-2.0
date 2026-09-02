"""
Discover county AP / check register files dropped in data/inbox/.

When found, transaction-level rules + Isolation Forest run via tools.transaction_anomaly.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.public_data_loaders import INGESTION, REPO_ROOT

INBOX = REPO_ROOT / "data" / "inbox"
EXTRACT_ROOT = INBOX / "extracted"

_AP_NAME_HINTS = re.compile(
    r"(ap[_\s-]?register|check[_\s-]?register|vendor[_\s-]?payment|"
    r"accounts[_\s-]?payable|payment[_\s-]?register|gl[_\s-]?detail)",
    re.I,
)


def _county_slug(county: str) -> str:
    return county.replace(" County", "").strip().lower().replace(" ", "_")


def ap_register_candidates(county: str) -> list[Path]:
    """Ordered search paths for transaction-level CSVs for one county."""
    slug = _county_slug(county)
    title = county.replace(" County", "").strip()
    names = [
        f"{title}_AP_Register.csv",
        f"{title}_CheckRegister.csv",
        f"{title}_vendor_payments.csv",
        f"{slug}_ap_register.csv",
        f"{slug}_check_register.csv",
        "ap_register.csv",
        "check_register.csv",
    ]
    paths: list[Path] = []
    for base in (INBOX, INGESTION, EXTRACT_ROOT):
        if not base.exists():
            continue
        for name in names:
            p = base / name
            if p.is_file():
                paths.append(p)
        for p in sorted(base.glob("*.csv")):
            low = p.name.lower()
            if slug in low and any(h in low for h in ("ap", "check", "vendor", "payment")):
                paths.append(p)
            elif _AP_NAME_HINTS.search(p.name):
                paths.append(p)
        for p in base.rglob("*.csv"):
            if p in paths:
                continue
            low = str(p).lower()
            if slug in low and _AP_NAME_HINTS.search(p.name):
                paths.append(p)
            elif _AP_NAME_HINTS.search(p.name) and slug in low:
                paths.append(p)

    seen: set[str] = set()
    unique: list[Path] = []
    for p in paths:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def looks_like_ap_register(path: Path) -> bool:
    """Quick header sniff — vendor + amount columns."""
    try:
        from tools.transaction_anomaly import load_transactions

        df = load_transactions(path)
        return len(df) >= 10 and "amount" in df.columns
    except Exception:
        return False


def best_ap_register(county: str) -> Path | None:
    for path in ap_register_candidates(county):
        if looks_like_ap_register(path):
            return path
    return None
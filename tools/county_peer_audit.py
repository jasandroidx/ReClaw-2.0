"""
Statewide peer comparison — flag counties that are outliers vs all 92 Indiana peers.

Uses Gateway certified budget totals and disbursement totals per capita.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from core.handoff import RedFlag
from tools.indiana_county_budget import load_county_budget_totals_series
from tools.public_data_loaders import REPO_ROOT, gateway_disbursement_stats
from tools.local_auditor_live import fetch_census

WORKLIST = REPO_ROOT / "data" / "indiana_county_worklist.yaml"
CACHE = REPO_ROOT / "data" / "cache"
_CENSUS_CACHE: dict[str, int] = {}


def _load_counties() -> list[dict]:
    import yaml

    data = yaml.safe_load(WORKLIST.read_text())
    return data.get("counties", [])


def _peer_metrics(year: int = 2024) -> list[dict]:
    """Per-county budget total + disbursement total + population."""
    metrics: list[dict] = []
    for c in _load_counties():
        name = c["name"]
        pop = 0
        fips = c.get("fips", "")
        if fips and len(fips) >= 5:
            if fips not in _CENSUS_CACHE:
                census = fetch_census(state_fips=fips[:2], county_fips3=fips[2:])
                _CENSUS_CACHE[fips] = int(census.get("population") or 0)
            pop = _CENSUS_CACHE[fips]

        series = load_county_budget_totals_series(name, gateway_code=c.get("gateway_code"), years=[year])
        budget = series[0]["amount"] if series else 0

        disb_path = CACHE / f"gateway_disbursements_{year}.txt"
        disb_total = 0.0
        if disb_path.exists():
            stats, _ = gateway_disbursement_stats(disb_path, county_name=name)
            disb_total = float(stats.get("total_disbursed") or 0)

        if budget <= 0 and disb_total <= 0:
            continue
        metrics.append(
            {
                "name": name,
                "gateway_code": c.get("gateway_code"),
                "population": pop or 1,
                "budget": budget,
                "disbursements": disb_total,
                "budget_per_capita": budget / max(pop, 1),
                "disb_per_capita": disb_total / max(pop, 1),
            }
        )
    return metrics


def _robust_z(values: list[float], target: float) -> float:
    arr = np.array(values, dtype=float)
    med = np.median(arr)
    mad = np.median(np.abs(arr - med))
    if mad < 1e-9:
        return 0.0
    return float(0.6745 * (target - med) / mad)


def detect_peer_outliers(
    county: str,
    year: int = 2024,
) -> list[RedFlag]:
    """Flag if target county is statistical outlier vs all IN peers."""
    metrics = _peer_metrics(year)
    if len(metrics) < 10:
        return []

    target = next((m for m in metrics if m["name"].lower() == county.lower()), None)
    if not target:
        return []

    flags: list[RedFlag] = []
    for field, label in (
        ("budget_per_capita", "certified budget per capita"),
        ("disb_per_capita", "disbursements per capita"),
    ):
        peers = [m[field] for m in metrics if m[field] > 0]
        z = _robust_z(peers, target[field])
        if abs(z) >= 2.0:
            rank = sum(1 for p in peers if p < target[field]) + 1
            flags.append(
                RedFlag(
                    severity="high" if abs(z) >= 3.0 else "medium",
                    category="peer_outlier",
                    description=(
                        f"{county} County ranks #{rank}/{len(peers)} in Indiana for "
                        f"{label} (${target[field]:,.0f}/resident, z={z:+.1f}σ vs peers)."
                    ),
                    evidence=json.dumps(
                        {
                            "metric": field,
                            "value": target[field],
                            "z_score": round(z, 2),
                            "rank": rank,
                            "peer_count": len(peers),
                            "year": year,
                        }
                    ),
                    recommended_action="Compare to adjacent counties; explain in budget hearing footage.",
                )
            )

    # ECOD on peer matrix when pyod available
    try:
        from pyod.models.ecod import ECOD

        X = np.array([[m["budget_per_capita"], m["disb_per_capita"]] for m in metrics])
        ecod = ECOD()
        ecod.fit(X)
        idx = next(i for i, m in enumerate(metrics) if m["name"].lower() == county.lower())
        if ecod.labels_[idx] == 1:
            flags.append(
                RedFlag(
                    severity="high",
                    category="peer_outlier",
                    description=(
                        f"{county} County: ECOD flagged as multivariate outlier among "
                        f"{len(metrics)} Indiana counties (budget + disbursement profile)."
                    ),
                    evidence=f"Statewide peer ECOD; year={year}",
                    recommended_action="Lead with 'how does your county compare to neighbors?' angle.",
                )
            )
    except ImportError:
        pass

    return flags


def rank_counties_for_content(year: int = 2024, top_n: int = 10) -> list[dict]:
    """Top counties by peer-outlier score — for 'Top 5 Indiana anomalies' shorts."""
    metrics = _peer_metrics(year)
    if not metrics:
        return []

    budget_vals = [m["budget_per_capita"] for m in metrics]
    disb_vals = [m["disb_per_capita"] for m in metrics]
    scored = []
    for m in metrics:
        zb = abs(_robust_z(budget_vals, m["budget_per_capita"]))
        zd = abs(_robust_z(disb_vals, m["disb_per_capita"]))
        scored.append({**m, "outlier_score": round(zb + zd, 2)})
    scored.sort(key=lambda x: -x["outlier_score"])
    return scored[:top_n]
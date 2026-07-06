"""
Unified red-flag engine — taxonomy-driven, county-equal, all layers.

Layers:
  1. local_auditor_live (Gateway disbursements, USASpending, Census, ProPublica)
  2. taxpayer_red_flags (budgets, salaries, fund mix, YoY disbursements)
  3. DOGEGPT budget anomalies (Gateway certified → ECOD/IF/YoY)
  4. Data-gap transparency flags
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from core.handoff import Insight, RedFlag, ResearchPackage
from tools.county_data_fetch import fetch_county_data, resolve_county
from tools.public_data_loaders import REPO_ROOT, load_budget_anomaly_excerpts
from tools.taxpayer_red_flags import TaxpayerScanResult, scan_taxpayer_red_flags

TAXONOMY_PATH = REPO_ROOT / "data" / "red_flag_taxonomy.yaml"


@dataclass
class RedFlagScanResult:
    county: str
    red_flags: list[RedFlag] = field(default_factory=list)
    insights: list[Insight] = field(default_factory=list)
    content_angles: list[str] = field(default_factory=list)
    video_titles: list[str] = field(default_factory=list)
    budget_implications: list[str] = field(default_factory=list)
    sources_used: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    anomaly_count: int = 0


def load_taxonomy() -> dict:
    if not TAXONOMY_PATH.exists():
        return {}
    return yaml.safe_load(TAXONOMY_PATH.read_text()) or {}


def _priority_sort(flags: list[RedFlag], taxonomy: dict) -> list[RedFlag]:
    order = taxonomy.get("video_priority") or []
    rank = {cat: i for i, cat in enumerate(order)}

    def key(f: RedFlag) -> tuple:
        sev = {"high": 0, "medium": 1, "low": 2}.get(f.severity, 3)
        return (sev, rank.get(f.category, 99))

    return sorted(flags, key=key)


def _gap_flags(gaps: list[str]) -> list[RedFlag]:
    flags = []
    for g in gaps:
        flags.append(
            RedFlag(
                severity="low" if "salary" in g.lower() else "medium",
                category="data_gap",
                description=g,
                evidence="Expected public record missing — transparency red flag",
                recommended_action="Export from Gateway or drop file in data/inbox/",
            )
        )
    return flags


def _dogegpt_flags(county: str) -> tuple[list[RedFlag], list[str], int]:
    """Run DOGEGPT pipeline and convert to RedFlags + script angles."""
    flags: list[RedFlag] = []
    angles: list[str] = []
    try:
        from tools.dogegpt_budget import run_county_anomalies

        path, n = run_county_anomalies(county)
        if not path or not path.exists():
            return flags, angles, 0

        import csv

        with path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                method = row.get("method", "")
                score = float(row.get("score") or 0)
                sev = "high" if method in ("ECOD", "YoY_spike") and score > 20 else "medium"
                desc = row.get("script_line") or row.get("note", "")
                flags.append(
                    RedFlag(
                        severity=sev,
                        category="statistical_anomaly" if method != "YoY_spike" else "budget_spike",
                        description=desc[:500],
                        evidence=f"DOGEGPT {method} → {path.name}",
                        recommended_action="Pull certified budget PDF + council votes for that fund/year.",
                    )
                )
                if row.get("script_line"):
                    angles.append(row["script_line"])
        return flags, angles, n
    except Exception:
        # Fallback: pre-computed anomalies.csv filtered by county
        excerpts, _ = load_budget_anomaly_excerpts(county=county)
        for line in excerpts:
            flags.append(
                RedFlag(
                    severity="high" if "ECOD" in line or "IsolationForest" in line else "medium",
                    category="statistical_anomaly",
                    description=line,
                    evidence="ingestion/anomalies.csv",
                    recommended_action="Verify fund lines in Gateway budget export.",
                )
            )
            angles.append(line)
        return flags, angles, len(excerpts)


def scan_all_red_flags(
    research: ResearchPackage | None = None,
    *,
    county: str | None = None,
    cache_dir: Path | None = None,
    include_live_auditor: bool = True,
) -> RedFlagScanResult:
    """
    Full taxonomy-driven scan for one county.
    Pass research package when available; otherwise county name only.
    """
    county = county or (research.county if research else "Pike")
    cache_dir = cache_dir or REPO_ROOT / "data" / "cache"
    taxonomy = load_taxonomy()
    meta = resolve_county(county) or {}
    bundle = fetch_county_data(county, gateway_code=meta.get("gateway_code"), fips=meta.get("fips"))

    all_flags: list[RedFlag] = []
    all_insights: list[Insight] = []
    all_angles: list[str] = []
    all_titles: list[str] = []
    all_impl: list[str] = []
    sources: list[str] = []

    # Layer 1: live multi-source auditor
    if include_live_auditor:
        try:
            from tools.local_auditor_live import audit_county_by_name

            audit = audit_county_by_name(county, state="IN")
            all_flags.extend(audit.red_flags)
            sources.extend(audit.sources_used)
        except Exception:
            pass

    # Layer 2: taxpayer heuristics
    if research:
        taxpayer: TaxpayerScanResult = scan_taxpayer_red_flags(research, cache_dir=cache_dir)
    else:
        # Minimal research shell for taxpayer scan
        from core.handoff import ResearchPackage as RP

        research = RP(
            county=county,
            primary_area=county,
            budgets=bundle.budgets,
            salaries=bundle.salaries,
        )
        taxpayer = scan_taxpayer_red_flags(research, cache_dir=cache_dir)

    all_flags.extend(taxpayer.red_flags)
    all_insights.extend(taxpayer.insights)
    all_angles.extend(taxpayer.content_angles)
    all_titles.extend(taxpayer.video_titles)
    all_impl.extend(taxpayer.budget_implications)

    # Layer 3: DOGEGPT budget anomalies
    dg_flags, dg_angles, anom_n = _dogegpt_flags(county)
    all_flags.extend(dg_flags)
    all_angles.extend(dg_angles)

    # Layer 3b: DOGEGPT cross-section patterns (composition + collective)
    try:
        from tools.composition_break import detect_collective_anomalies, detect_composition_breaks

        all_flags.extend(
            detect_composition_breaks(county, gateway_code=meta.get("gateway_code"))
        )
        all_flags.extend(
            detect_collective_anomalies(county, gateway_code=meta.get("gateway_code"))
        )
    except Exception:
        pass

    # Layer 3c: Split-purchase (IC 36-1-12-19)
    try:
        from tools.split_purchase_detector import detect_split_purchases

        all_flags.extend(detect_split_purchases(county, year=2024, cache_dir=cache_dir))
    except Exception:
        pass

    # Layer 3d: Statewide peer outlier
    try:
        from tools.county_peer_audit import detect_peer_outliers

        all_flags.extend(detect_peer_outliers(county))
    except Exception:
        pass

    # Layer 4: data gaps
    all_flags.extend(_gap_flags(bundle.gaps))

    # Dedupe by description
    seen: set[str] = set()
    unique_flags: list[RedFlag] = []
    for f in _priority_sort(all_flags, taxonomy):
        key = f"{f.category}:{f.description[:80]}"
        if key in seen:
            continue
        seen.add(key)
        unique_flags.append(f)

    seen_a: set[str] = set()
    unique_angles = []
    for a in all_angles:
        if a and a not in seen_a:
            seen_a.add(a)
            unique_angles.append(a)

    return RedFlagScanResult(
        county=county,
        red_flags=unique_flags,
        insights=all_insights,
        content_angles=unique_angles,
        video_titles=all_titles,
        budget_implications=all_impl,
        sources_used=sources,
        gaps=bundle.gaps,
        anomaly_count=anom_n,
    )
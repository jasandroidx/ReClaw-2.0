"""
Researcher Agent — ReClaw 2.0

Mission: Pull public county / municipal data for rural areas (property, budgets, payroll).
Output: Clean, validated ResearchPackage (JSON + summary).

Current scope (MVP):
- Pike County IN + Winslow focus (expand via config later)
- Strong seed data so it runs 100% offline / on first deploy
- Live fetch is stubbed but structured for easy extension (requests + bs4)
- Never hallucinates numbers. If data missing, mark it.

Handoff contract: returns ResearchPackage (see core/handoff.py)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup  # soft dep — only used if use_live_fetch

from core.config import get_settings
from core.handoff import (
    BudgetData,
    PropertyRecord,
    ResearchPackage,
    SalaryEntry,
    SourceRef,
)
from core.security import SecurityManager
from core.session import Session
from tools.public_data_loaders import (
    gateway_disbursement_stats,
    load_budget_anomaly_excerpts,
    load_multi_year_budget_totals,
    load_pike_budgets_from_textmode,
    load_pike_budgets_multi_year,
    load_pike_salaries_from_gateway_export,
    load_salary_detail_records,
)


PIKE_WINSLOW_SEED: dict[str, Any] = {
    "county": "Pike",
    "primary_area": "Winslow",
    "state": "IN",
    "sources": [
        {
            "kind": "seed",
            "note": "Pike County IN rural data seed v1 — 2025 snapshot for ReClaw dev & testing",
            "fetched_at": "2026-06-04T12:00:00Z",
        },
        {
            "kind": "seed",
            "note": "Simulated public records from county auditor / GIS style exports",
        },
    ],
    "property_records": [
        {
            "parcel_id": "63-07-14-100-001.000-001",
            "address": "1234 S County Road 50 W",
            "city": "Winslow",
            "land_acres": 12.4,
            "assessed_value": 48500,
            "land_value": 31200,
            "improvement_value": 17300,
            "property_class": "agricultural",
            "year_built": 1978,
            "last_sale_date": "2019-03-12",
            "last_sale_price": 42000,
            "notes": "Mostly tillable, small barn, no well currently active",
        },
        {
            "parcel_id": "63-07-22-300-005.000-001",
            "address": "487 E Main St",
            "city": "Winslow",
            "land_acres": 0.6,
            "assessed_value": 28500,
            "land_value": 8500,
            "improvement_value": 20000,
            "property_class": "residential",
            "year_built": 1945,
            "last_sale_date": "2023-08-05",
            "last_sale_price": 26500,
            "notes": "Town lot, needs roof work. Good candidate for 'fixer rural starter'",
        },
        {
            "parcel_id": "63-08-05-200-012.000-002",
            "address": "8900 N State Road 61",
            "city": "Winslow",
            "land_acres": 47.0,
            "assessed_value": 124000,
            "land_value": 98500,
            "improvement_value": 25500,
            "property_class": "agricultural",
            "year_built": 1962,
            "notes": "Large parcel, two outbuildings, creek access. Rare for under $150k.",
        },
        {
            "parcel_id": "63-07-11-400-008.000-001",
            "address": "215 W Water St",
            "city": "Winslow",
            "land_acres": 0.3,
            "assessed_value": 19200,
            "land_value": 4200,
            "improvement_value": 15000,
            "property_class": "residential",
            "year_built": 1928,
            "notes": "Very low entry price. High risk of foundation issues per local chatter.",
        },
    ],
    "budgets": [
        {
            "fiscal_year": 2025,
            "entity": "Pike County",
            "total_revenue": 4875000,
            "total_expenditures": 5023000,
            "surplus_deficit": -148000,
            "major_funds": {
                "General": 2150000,
                "Road & Bridge": 980000,
                "Cumulative Bridge": 420000,
                "Health": 185000,
            },
            "revenue_sources": {
                "Property Tax": 2650000,
                "Local Income Tax": 980000,
                "State Distributions": 720000,
                "Fees & Misc": 525000,
            },
            "expenditure_categories": {
                "Public Safety": 1450000,
                "Highways/Roads": 1120000,
                "General Gov": 890000,
                "Health & Welfare": 410000,
                "Debt Service": 320000,
            },
            "notes": "Slight deficit. Road maintenance and bridge projects are the big pressure items. Property tax levy up ~4.2% YoY.",
        },
        {
            "fiscal_year": 2025,
            "entity": "Winslow Town",
            "total_revenue": 312000,
            "total_expenditures": 298000,
            "surplus_deficit": 14000,
            "major_funds": {"General": 185000, "Utility": 127000},
            "notes": "Small town, surprisingly balanced. Heavy reliance on utility transfers.",
        },
    ],
    "salaries": [
        {
            "department": "Sheriff",
            "position": "Deputy Sheriff",
            "employee_count": 6,
            "avg_salary": 47800,
            "min_salary": 41500,
            "max_salary": 54200,
            "year": 2025,
        },
        {
            "department": "Highway",
            "position": "Road Worker / Operator",
            "employee_count": 4,
            "avg_salary": 41200,
            "min_salary": 36500,
            "max_salary": 48900,
            "year": 2025,
        },
        {
            "department": "Auditor / Clerk",
            "position": "Deputy Auditor",
            "employee_count": 2,
            "avg_salary": 38500,
            "year": 2025,
        },
    ],
    "summary": (
        "Pike County (pop ~12,200) shows classic rural Indiana patterns: low property values, "
        "ag-heavy tax base, and tightening budgets. Winslow (pop ~780) has extremely affordable "
        "entry points — multiple habitable parcels under $30k. County is running a modest deficit "
        "in 2025 driven by road/bridge needs. Public payroll is lean; deputy and road crew pay "
        "hovers in the low-to-mid $40ks. Several large ag parcels remain surprisingly cheap by "
        "national standards, creating both opportunity and 'why is it still available' questions."
    ),
}


class ResearcherAgent:
    """
    Primary data gatherer.

    OpenClaw-aligned:
    - Loads its own SOUL.md at init (for identity + logging)
    - Runs inside a Session for isolation
    - Uses SecurityManager for approval gates on live_fetch

    Usage (with session - preferred):
        sess = Session()
        researcher = ResearcherAgent(session=sess)
        pkg = researcher.run(county="Pike", area="Winslow")

    Or simple:
        researcher = ResearcherAgent()
        pkg = researcher.run(...)
    """

    SOUL_PATH = Path(__file__).parent / "researcher" / "SOUL.md"

    def __init__(self, settings: Any | None = None, session: Session | None = None):
        self.settings = settings or get_settings()
        self.session = session
        self.security: SecurityManager | None = None
        if self.session:
            self.security = SecurityManager(self.session.base_dir, self.session.session_id)
            soul_text = self.session.load_soul("researcher", self.SOUL_PATH)
            self.session.log(f"Researcher SOUL loaded (len={len(soul_text)} chars)")
        self.client = httpx.Client(timeout=self.settings.fetch_timeout, follow_redirects=True)

    def run(self, county: str = "Pike", area: str = "Winslow", force_seed: bool = False) -> ResearchPackage:
        """
        Main entry. Returns a validated ResearchPackage.
        Priority: real public data (ingestion/) → live Gateway download → seeds (last resort).
        """
        if not force_seed:
            from tools.county_data_fetch import resolve_county

            if resolve_county(county) or county.lower() == "pike":
                pkg = self._build_from_county_data(county, area)
                if pkg.budgets or pkg.salaries or pkg.raw_excerpts:
                    if self.session:
                        self.session.write_handoff("researcher", pkg)
                        if self.security:
                            self.security.record_action(
                                "public_data_live_fetch",
                                {
                                    "county": county,
                                    "mode": "county_data_fetch",
                                    "budgets": len(pkg.budgets),
                                    "salaries": len(pkg.salaries),
                                },
                            )
                    return pkg

        use_live = self.settings.use_live_fetch and not force_seed
        if use_live:
            if self.security:
                if not self.security.is_granted("public_data_live_fetch"):
                    req = self.security.request_approval(
                        "public_data_live_fetch",
                        reason=f"Live fetch requested for {county}/{area} (settings.use_live_fetch=True)",
                        agent="researcher",
                    )
                    msg = f"Live fetch requires approval. Pending request: {req.id}. Falling back."
                    print(f"[Researcher] {msg}")
                    if self.session:
                        self.session.log(msg)
                    use_live = False
                else:
                    self.security.record_action("public_data_live_fetch", {"county": county, "area": area})

            if use_live:
                try:
                    pkg = self._attempt_live_fetch(county, area)
                    if pkg and (pkg.property_records or pkg.budgets):
                        if self.session:
                            self.session.write_handoff("researcher", pkg)
                        return pkg
                except Exception as e:
                    print(f"[Researcher] Live fetch failed: {e}. Falling back to seed.")

        pkg = self._build_from_seed(county, area)
        if self.session:
            self.session.write_handoff("researcher", pkg)
            if self.security:
                self.security.record_action("public_data_seed", {"county": county, "records": len(pkg.property_records)})
        return pkg

    def _build_from_county_data(self, county: str, area: str, year: int = 2025) -> ResearchPackage:
        """Load real public data for any Indiana county via county_data_fetch."""
        from tools.county_data_fetch import fetch_county_data, resolve_county

        meta = resolve_county(county) or {}
        bundle = fetch_county_data(
            county,
            gateway_code=meta.get("gateway_code"),
            fips=meta.get("fips"),
        )
        sources: list[SourceRef] = list(bundle.sources)
        budgets: list[BudgetData] = list(bundle.budgets)
        salaries: list[SalaryEntry] = list(bundle.salaries)
        excerpts: list[str] = []

        for t in bundle.budget_series:
            line = f"FY{t['year']} certified total: ${t['amount']:,}"
            if t.get("yoy_pct") is not None:
                line += f" ({t['yoy_pct']:+.1f}% YoY)"
            excerpts.append(line)

        if bundle.gateway_stats:
            s = bundle.gateway_stats
            excerpts.append(
                f"Gateway disbursements: {s.get('transaction_lines', 0)} lines, "
                f"${s.get('total_disbursed', 0):,.0f} total."
            )

        if bundle.salary_records:
            top3 = sorted(bundle.salary_records, key=lambda r: r["compensation"], reverse=True)[:3]
            for rec in top3:
                excerpts.append(
                    f"Top pay: {rec['name']} — {rec['job_title']} (${rec['compensation']:,})"
                )

        try:
            from tools.dogegpt_budget import run_county_anomalies

            run_county_anomalies(county)
            anom_ex, anom_src = load_budget_anomaly_excerpts(county=county)
            excerpts.extend(anom_ex[:10])
            sources.extend(anom_src)
        except Exception:
            anom_ex, anom_src = load_budget_anomaly_excerpts(county=county)
            excerpts.extend(anom_ex)
            sources.extend(anom_src)

        for gap in bundle.gaps:
            excerpts.append(f"DATA GAP: {gap}")

        # Pike ingestion CSVs still supplement when present (richer fund detail)
        if county.lower() == "pike":
            return self._merge_pike_ingestion(county, area, year, budgets, salaries, sources, excerpts)

        seed = self._build_from_seed(county, area)
        props = seed.property_records
        for p in props:
            suffix = " [GIS: verify at beacon.schneidercorp.com — seed until live GIS wired]"
            p.notes = p.notes + suffix if p.notes else suffix
        sources.append(
            SourceRef(
                kind="web",
                url="https://beacon.schneidercorp.com/",
                note="Parcel examples from seed until county GIS automated",
            )
        )

        summary_parts = [
            f"{county} County FY{year} research from Indiana public sources "
            f"(Gateway certified budgets, disbursements, federal/demographic context)."
        ]
        if budgets:
            top = budgets[0]
            summary_parts.append(
                f"Certified budget total FY{top.fiscal_year}: ${top.total_expenditures:,}."
            )
        if salaries:
            top = max(salaries, key=lambda x: x.max_salary or 0)
            summary_parts.append(
                f"Public payroll sample: {top.department} max ${top.max_salary:,}."
            )
        if bundle.gaps:
            summary_parts.append(f"Gaps: {len(bundle.gaps)} (see raw_excerpts).")

        return ResearchPackage(
            county=county,
            primary_area=area,
            state="IN",
            sources=sources,
            property_records=props[: self.settings.max_properties_per_county],
            budgets=budgets,
            salaries=salaries,
            summary=" ".join(summary_parts),
            raw_excerpts=excerpts,
        )

    def _merge_pike_ingestion(
        self,
        county: str,
        area: str,
        year: int,
        budgets: list[BudgetData],
        salaries: list[SalaryEntry],
        sources: list[SourceRef],
        excerpts: list[str],
    ) -> ResearchPackage:
        """Pike: merge Gateway fetch with legacy ingestion/ detail when on disk."""
        pkg = self._build_from_public_data(county, area, year)
        if budgets and not pkg.budgets:
            pkg.budgets = budgets
        elif budgets:
            pkg.budgets = budgets + [b for b in pkg.budgets if b not in budgets]
        if salaries and not pkg.salaries:
            pkg.salaries = salaries
        pkg.raw_excerpts = excerpts + pkg.raw_excerpts
        for s in sources:
            if not any(x.note == s.note for x in pkg.sources):
                pkg.sources.append(s)
        return pkg

    def _build_from_public_data(self, county: str, area: str, year: int = 2025) -> ResearchPackage:
        """Load Pike ingestion/ caches + optional Gateway download. Pike County ONLY."""
        from tools.county_isolation import is_pike

        if not is_pike(county):
            raise ValueError(f"_build_from_public_data is Pike-only; got {county}")
        sources: list[SourceRef] = []
        budgets: list[BudgetData] = []
        salaries: list[SalaryEntry] = []
        excerpts: list[str] = []

        hist, hist_src = load_pike_budgets_multi_year(years=[2022, 2023, 2024])
        budgets.extend(hist)
        sources.extend(hist_src)

        b, b_src = load_pike_budgets_from_textmode(fiscal_year=year)
        budgets.extend(b)
        for src in b_src:
            if not any(x.note == src.note for x in sources):
                sources.append(src)

        trend = load_multi_year_budget_totals()
        for t in trend:
            line = f"FY{t['year']} certified total: ${t['amount']:,}"
            if t.get("yoy_pct") is not None:
                line += f" ({t['yoy_pct']:+.1f}% YoY)"
            excerpts.append(line)

        s, s_src = load_pike_salaries_from_gateway_export(fiscal_year=year)
        salaries.extend(s)
        for src in s_src:
            if not any(x.note == src.note for x in sources):
                sources.append(src)

        anom_ex, anom_src = load_budget_anomaly_excerpts(county=county)
        excerpts.extend(anom_ex)
        sources.extend(anom_src)

        salary_records = load_salary_detail_records()
        if salary_records:
            top3 = sorted(salary_records, key=lambda r: r["compensation"], reverse=True)[:3]
            for rec in top3:
                excerpts.append(
                    f"Top pay: {rec['name']} — {rec['job_title']} (${rec['compensation']:,})"
                )

        gateway_path = self._gateway_cache_path(year)
        if not gateway_path.exists() or self.settings.use_live_fetch:
            try:
                from tools.indiana_gateway import download_disbursements

                print(f"[Researcher] Downloading Indiana Gateway disbursements {year}...")
                download_disbursements(year, gateway_path)
                sources.append(
                    SourceRef(
                        kind="web",
                        url="https://gateway.ifionline.org/public/AFR.aspx",
                        note=f"Disbursements by Fund {year} → {gateway_path.name}",
                    )
                )
                if self.session:
                    self.session.log(f"Gateway disbursements {year} saved to {gateway_path}")
            except Exception as e:
                print(f"[Researcher] Gateway download failed: {e}")
                if self.session:
                    self.session.log(f"Gateway download failed: {e}", level="WARN")

        if gateway_path.exists():
            stats, gw_ex = gateway_disbursement_stats(gateway_path, county_name=county)
            if stats:
                excerpts.append(
                    f"Gateway disbursements: {stats['transaction_lines']} lines, "
                    f"${stats['total_disbursed']:,.0f} total, {stats['unique_vendors']} vendors."
                )
                excerpts.extend(gw_ex)

        # Property GIS still manual — use seed parcels but label provenance honestly
        seed = self._build_from_seed(county, area)
        props = seed.property_records
        for p in props:
            suffix = " [GIS: verify at beacon.schneidercorp.com — seed parcel until live GIS wired]"
            p.notes = p.notes + suffix if p.notes else suffix
        sources.append(
            SourceRef(
                kind="web",
                url="https://beacon.schneidercorp.com/",
                note="Parcel examples from dev seed; replace with Beacon GIS pull when automated",
            )
        )

        total_pike = next((b.total_expenditures for b in budgets if b.entity == "Pike County"), None)
        winslow_total = next((b.total_expenditures for b in budgets if "Winslow" in b.entity), None)
        summary_parts = [
            f"Pike County FY{year} research from REAL public sources (DOR budget certification, "
            f"Gateway salary transparency, DOGEGPT anomaly pipeline)."
        ]
        if total_pike:
            summary_parts.append(f"County certified budget total: ${total_pike:,}.")
        if winslow_total:
            summary_parts.append(f"Winslow Civil Town certified funds: ${winslow_total:,}.")
        if salaries:
            top = max(salaries, key=lambda x: x.max_salary or 0)
            summary_parts.append(
                f"Public payroll sample: {top.department} max comp ${top.max_salary:,} "
                f"({top.employee_count} records in export)."
            )
        summary_parts.append(
            "Corruption/watchdog angles: see raw_excerpts for ECOD/IsolationForest flags and top vendors."
        )

        return ResearchPackage(
            county=county,
            primary_area=area,
            state="IN",
            sources=sources,
            property_records=props[: self.settings.max_properties_per_county],
            budgets=budgets,
            salaries=salaries,
            summary=" ".join(summary_parts),
            raw_excerpts=excerpts,
        )

    def _gateway_cache_path(self, year: int) -> Path:
        if self.session:
            src_dir = self.session.base_dir / "sources"
            src_dir.mkdir(parents=True, exist_ok=True)
            return src_dir / f"gateway_disbursements_{year}.txt"
        cache = self.settings.data_dir / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        return cache / f"gateway_disbursements_{year}.txt"

    def _build_from_seed(self, county: str, area: str) -> ResearchPackage:
        seed = PIKE_WINSLOW_SEED.copy()
        # allow future override by county key if we add more seeds
        pkg = ResearchPackage(
            county=seed["county"],
            primary_area=seed["primary_area"],
            state=seed.get("state", "IN"),
            sources=[SourceRef(**s) for s in seed.get("sources", [])],
            property_records=[PropertyRecord(**p) for p in seed.get("property_records", [])],
            budgets=[BudgetData(**b) for b in seed.get("budgets", [])],
            salaries=[SalaryEntry(**s) for s in seed.get("salaries", [])],
            summary=seed.get("summary", ""),
        )
        # trim if configured
        if len(pkg.property_records) > self.settings.max_properties_per_county:
            pkg.property_records = pkg.property_records[: self.settings.max_properties_per_county]
        return pkg

    def _attempt_live_fetch(self, county: str, area: str) -> ResearchPackage | None:
        """
        Placeholder for real public data pulls.

        Real targets you would add (Pike IN examples):
        - County GIS / Beacon: https://beacon.schneidercorp.com/ (county selector)
        - Pike County IN site: https://www.pikecounty.in.gov/
        - Indiana transparency / budget portals
        - Auditor / Treasurer PDF budgets (parse with pypdf or camelot)

        For v1 we keep this as a clean extension point. Implement one source at a time.
        """
        sources: list[SourceRef] = []
        props: list[PropertyRecord] = []
        budgets: list[BudgetData] = []
        salaries: list[SalaryEntry] = []

        # Example stub — a county site that might have a simple property search or news
        # In prod you would do proper parsing + pagination + rate limiting + robots respect.
        if county.lower() == "pike" and self.settings.use_live_fetch:
            try:
                # This is a real-ish public county site (example; adjust as needed)
                resp = self.client.get("https://www.pikecounty.in.gov/", headers={"User-Agent": "ReClaw/2.0 (+rural data research)"})
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Very naive extraction just to prove the pipeline
                    soup.get_text(" ", strip=True)[:1500]
                    sources.append(SourceRef(kind="web", url="https://www.pikecounty.in.gov/", note="homepage scrape for freshness check"))
                    # We still return seed-augmented in this stub because full scrape is out of scope for MVP
                    # In a real iteration you would parse tables here and append to props/budgets.
            except Exception:
                pass  # silent — we always want to return something

        if not props and not budgets:
            return None

        return ResearchPackage(
            county=county,
            primary_area=area,
            sources=sources,
            property_records=props,
            budgets=budgets,
            salaries=salaries,
            summary="Live fetch partial (see sources). Full structured data still from seed for this run.",
        )

    def dump_seed_to_file(self, path: Path | None = None) -> Path:
        """Utility: write the current PIKE_WINSLOW_SEED to disk for inspection / versioning."""
        p = path or (self.settings.seeds_dir / "pike_county_winslow_2025.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(PIKE_WINSLOW_SEED, indent=2, ensure_ascii=False), encoding="utf-8")
        return p

    def close(self):
        self.client.close()

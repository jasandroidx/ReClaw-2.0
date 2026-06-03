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
from datetime import datetime
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
from core.security import SecurityManager, get_capability
from core.session import Session


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
        Respects security gates for live actions.
        """
        use_live = self.settings.use_live_fetch and not force_seed

        if use_live:
            # Gate check (OpenClaw approval pattern)
            if self.security:
                if not self.security.is_granted("public_data_live_fetch"):
                    req = self.security.request_approval(
                        "public_data_live_fetch",
                        reason=f"Live fetch requested for {county}/{area} (settings.use_live_fetch=True)",
                        agent="researcher"
                    )
                    msg = f"Live fetch requires approval. Pending request: {req.id}. Falling back to seed for safety."
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

        # Seed / deterministic path (always works, low privilege)
        pkg = self._build_from_seed(county, area)
        if self.session:
            self.session.write_handoff("researcher", pkg)
            self.security.record_action("public_data_seed", {"county": county, "records": len(pkg.property_records)})
        return pkg

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
                    text = soup.get_text(" ", strip=True)[:1500]
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

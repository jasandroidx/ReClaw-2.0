"""
Firecrawl Tier-3 discovery layer — county sites, SBOA, DOR (NOT Gateway flat files).

Use for: finding PDFs, meeting minutes, bid announcements, audit report links.
Do NOT use for: Gateway disbursements/budgets (use indiana_gateway.py flat files).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from tools.public_data_loaders import REPO_ROOT

DISCOVERY_CACHE = REPO_ROOT / "data" / "cache" / "firecrawl"
INBOX = REPO_ROOT / "data" / "inbox" / "firecrawl"

# Indiana audit discovery targets (Tier 3)
COUNTY_SITE_TEMPLATE = "https://www.{county_lower}county.in.gov/"
SBOA_SEARCH = "https://www.in.gov/sboa/resources/reports/"
DOR_BUDGET_ORDERS = "https://www.in.gov/dor/budget-and-claims/budget-orders/"


def _api_key() -> str:
    return os.environ.get("FIRECRAWL_API_KEY", "").strip()


def _client():
    key = _api_key()
    if not key:
        raise RuntimeError(
            "FIRECRAWL_API_KEY missing — get one at https://firecrawl.dev "
            "and add to /root/ReClaw-2.0/.env"
        )
    from firecrawl import FirecrawlApp

    return FirecrawlApp(api_key=key)


def scrape_url(url: str, *, formats: list[str] | None = None) -> dict:
    """Scrape one page to markdown + links."""
    app = _client()
    formats = formats or ["markdown", "links"]
    result = app.scrape(url, formats=formats)
    if isinstance(result, dict):
        return result
    return getattr(result, "model_dump", lambda: {"raw": str(result)})()


def map_site(url: str, *, limit: int = 100) -> list[str]:
    """Discover URLs on a site (budget PDFs, minutes, etc.)."""
    app = _client()
    result = app.map(url, limit=limit)
    links = result.get("links", []) if isinstance(result, dict) else []
    return [l if isinstance(l, str) else l.get("url", "") for l in links]


def _pdf_links(links: list[str]) -> list[str]:
    return [u for u in links if u.lower().endswith(".pdf")]


def discover_county_context(county: str) -> dict:
    """
    Crawl county .in.gov site for PDFs and narrative context.
    Returns manifest dict; does not download binaries (use inbox for that).
    """
    name = county.replace(" County", "").strip().lower()
    url = COUNTY_SITE_TEMPLATE.format(county_lower=name)
    DISCOVERY_CACHE.mkdir(parents=True, exist_ok=True)

    out: dict = {
        "county": county,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "county_url": url,
        "pdfs": [],
        "links_sample": [],
        "markdown_excerpt": "",
        "error": None,
    }

    try:
        links = map_site(url, limit=80)
        pdfs = _pdf_links(links)
        out["pdfs"] = pdfs[:30]
        out["links_sample"] = links[:20]
        if pdfs:
            scrape = scrape_url(pdfs[0])
            out["markdown_excerpt"] = (scrape.get("markdown") or "")[:2000]
    except Exception as e:
        out["error"] = str(e)

    cache_path = DISCOVERY_CACHE / f"{name}_discovery.json"
    cache_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def discover_state_portals() -> dict:
    """Map DOR budget orders + SBOA report index for PDF discovery."""
    DISCOVERY_CACHE.mkdir(parents=True, exist_ok=True)
    manifest = {"scraped_at": datetime.now(timezone.utc).isoformat(), "portals": {}}

    for label, url in (("dor_budget_orders", DOR_BUDGET_ORDERS), ("sboa_reports", SBOA_SEARCH)):
        try:
            links = map_site(url, limit=150)
            manifest["portals"][label] = {
                "url": url,
                "pdf_count": len(_pdf_links(links)),
                "pdfs": _pdf_links(links)[:40],
                "links_sample": links[:15],
            }
        except Exception as e:
            manifest["portals"][label] = {"url": url, "error": str(e)}

    path = DISCOVERY_CACHE / "indiana_portals.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def flags_from_discovery(discovery: dict) -> list[str]:
    """Content angles from discovered PDFs/links."""
    angles: list[str] = []
    county = discovery.get("county", "County")
    for pdf in discovery.get("pdfs", [])[:5]:
        name = Path(urlparse(pdf).path).name
        if re.search(r"budget|audit|bid|minutes|levy", name, re.I):
            angles.append(f"{county}: public doc found — {name} ({pdf})")
    return angles
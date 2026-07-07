"""
SBOA audit report discovery + lightweight PDF ingest for Indiana counties.

Tier-3: narrative provenance beats statistical-only hooks ("SBOA already flagged X").
Uses Firecrawl map/scrape — does not replace Gateway math.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from core.handoff import RedFlag
from tools.public_data_loaders import REPO_ROOT

SBOA_BASE = "https://audit.sboa.in.gov"
SBOA_REPORTS = "https://www.in.gov/sboa/resources/reports/"
CACHE_ROOT = REPO_ROOT / "data" / "cache" / "sboa"

# Finding language that makes strong video hooks when cited with PDF page.
_FINDING_PATTERNS = re.compile(
    r"\b(material weakness|significant deficiency|noncompliance|finding|"
    r"recommendation|qualified opinion|adverse opinion|fraud|duplicate|"
    r"segregation of duties|bid|procurement|overpayment)\b",
    re.I,
)


def _county_slug(county: str) -> str:
    return county.replace(" County", "").strip()


def cache_dir(county: str) -> Path:
    slug = _county_slug(county).lower().replace(" ", "_")
    path = CACHE_ROOT / slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def manifest_path(county: str) -> Path:
    return cache_dir(county) / "manifest.json"


def load_manifest(county: str) -> dict:
    path = manifest_path(county)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"county": _county_slug(county), "pdfs": [], "findings": [], "scraped_at": None}


def _save_manifest(county: str, manifest: dict) -> Path:
    manifest["scraped_at"] = datetime.now(timezone.utc).isoformat()
    path = manifest_path(county)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def _pdf_name(url: str) -> str:
    return Path(urlparse(url).path).name or "report.pdf"


def discover_sboa_pdfs(county: str, *, limit: int = 40) -> dict:
    """
    Map SBOA report index + search for county-named audit PDFs.
    Caches manifest under data/cache/sboa/{county}/.
    """
    name = _county_slug(county)
    manifest = load_manifest(name)
    manifest["county"] = name
    manifest.setdefault("pdfs", [])
    manifest.setdefault("errors", [])

    try:
        from tools.firecrawl_discovery import map_site, scrape_url, _pdf_links

        # Site map for PDFs mentioning county
        links = map_site(SBOA_REPORTS, limit=limit)
        county_links = [
            u
            for u in links
            if name.lower() in u.lower() or name.lower().replace(" ", "") in u.lower()
        ]
        pdfs = _pdf_links(county_links) or _pdf_links(links)

        # Firecrawl search fallback
        try:
            from firecrawl import FirecrawlApp
            import os

            key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
            if key:
                app = FirecrawlApp(api_key=key)
                q = f"site:in.gov/sboa {name} County Indiana audit report"
                result = app.search(q, limit=10)
                web = result.get("web", []) if isinstance(result, dict) else []
                for hit in web:
                    url = hit.get("url") if isinstance(hit, dict) else ""
                    if url and url.lower().endswith(".pdf"):
                        pdfs.append(url)
        except Exception as e:
            manifest["errors"].append(f"search: {e}")

        seen: set[str] = set()
        unique_pdfs: list[dict] = []
        for url in pdfs:
            if url in seen:
                continue
            seen.add(url)
            unique_pdfs.append(
                {
                    "url": url,
                    "filename": _pdf_name(url),
                    "county_match": name.lower() in url.lower(),
                }
            )

        manifest["pdfs"] = unique_pdfs[:25]
        manifest["sboa_index"] = SBOA_REPORTS

        # Scrape first county-matched PDF for excerpt
        match = next((p for p in unique_pdfs if p.get("county_match")), None)
        if match:
            try:
                scrape = scrape_url(match["url"])
                excerpt = (scrape.get("markdown") or "")[:4000]
                manifest["excerpt"] = excerpt
                manifest["excerpt_source"] = match["url"]
            except Exception as e:
                manifest["errors"].append(f"scrape: {e}")
    except Exception as e:
        manifest["errors"].append(str(e))

    _save_manifest(name, manifest)
    return manifest


def extract_findings_from_text(text: str, *, source: str, county: str) -> list[dict]:
    """Pull sentence-level finding candidates from SBOA markdown/text."""
    findings: list[dict] = []
    for para in re.split(r"\n{2,}", text):
        para = para.strip()
        if len(para) < 40 or not _FINDING_PATTERNS.search(para):
            continue
        findings.append(
            {
                "county": county,
                "excerpt": para[:500],
                "source": source,
            }
        )
        if len(findings) >= 12:
            break
    return findings


def ingest_sboa_county(county: str, *, discover: bool = True) -> dict:
    """Discover PDFs + extract finding excerpts into manifest."""
    name = _county_slug(county)
    manifest = discover_sboa_pdfs(name) if discover else load_manifest(name)

    text = manifest.get("excerpt") or ""
    if not text and manifest.get("pdfs"):
        try:
            from tools.firecrawl_discovery import scrape_url

            scrape = scrape_url(manifest["pdfs"][0]["url"])
            text = scrape.get("markdown") or ""
            manifest["excerpt"] = text[:4000]
        except Exception:
            pass

    manifest["findings"] = extract_findings_from_text(
        text,
        source=manifest.get("excerpt_source") or SBOA_REPORTS,
        county=name,
    )
    _save_manifest(name, manifest)
    return manifest


def sboa_red_flags(county: str) -> list[RedFlag]:
    """Convert cached SBOA finding excerpts to RedFlags for red_flag_engine."""
    manifest = load_manifest(county)
    if not manifest.get("findings") and not manifest.get("pdfs"):
        return []

    flags: list[RedFlag] = []
    for i, finding in enumerate(manifest.get("findings", [])[:6]):
        flags.append(
            RedFlag(
                severity="high" if i < 2 else "medium",
                category="data_gap",
                description=(
                    f"SBOA prior report ({county}): {finding['excerpt'][:220]}…"
                ),
                evidence=json.dumps(
                    {
                        "source": finding.get("source"),
                        "type": "sboa_narrative",
                        "county": county,
                    }
                ),
                recommended_action="Cite PDF page in script; link in video description.",
            )
        )

    if not flags and manifest.get("pdfs"):
        top = manifest["pdfs"][0]
        flags.append(
            RedFlag(
                severity="medium",
                category="data_gap",
                description=(
                    f"{county} County: SBOA audit PDF on file — "
                    f"'{top.get('filename')}' (manual review for prior findings)"
                ),
                evidence=json.dumps({"url": top.get("url"), "type": "sboa_pdf_link"}),
                recommended_action="Scrape PDF and extract finding numbers for hook.",
            )
        )
    return flags
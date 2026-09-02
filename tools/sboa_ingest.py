"""
SBOA audit report discovery + PDF ingest for Indiana counties.

Primary path (no Firecrawl): POST https://audit.sboa.in.gov:8090/filings/search
PDF files: prefer https://www.in.gov/sboa/WebReports/{reportNumber}.pdf
  (same object IDs as audit.sboa.in.gov/WebReports/ — better TLS on in.gov)

Tier-3: narrative provenance for Story Factory Level-1 juice.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from core.handoff import RedFlag
from tools.public_data_loaders import REPO_ROOT

SBOA_API = "https://audit.sboa.in.gov:8090/filings/search"
SBOA_PDF_IN_GOV = "https://www.in.gov/sboa/WebReports/{filename}"
SBOA_PDF_AUDIT = "https://audit.sboa.in.gov/WebReports/{filename}"
SBOA_INDEX = "https://audit.sboa.in.gov/"
CACHE_ROOT = REPO_ROOT / "data" / "cache" / "sboa"

# Prefer special investigations and compliance for video juice.
_AUDIT_PRIORITY = {
    "SPECIAL INVESTIGATION REPORT": 0,
    "SPECIAL INVESTIGATION": 0,
    "SUPPLEMENTAL": 1,
    "FEDERAL SINGLE AUDIT": 2,
    "NONFEDERAL FINANCIAL AUDIT": 3,
    "FINANCIAL": 4,
}

# Finding language that makes strong video hooks when cited with PDF page.
_FINDING_PATTERNS = re.compile(
    r"\b("
    r"material weakness|significant deficiency|noncompliance|finding|"
    r"recommendation|qualified opinion|adverse opinion|"
    r"unsupported|overpayment|segregation of duties|"
    r"duplicate payment|credit card|nepotism|bid|procurement|"
    r"missing|misappropriat|personal (use|expense)|late fee|"
    r"internal control|compliance"
    r")\b",
    re.I,
)

# County key as used by API (camelCase for multi-word)
_COUNTY_API_KEY: dict[str, str] = {
    "saint joseph": "Saint Joseph",
    "st joseph": "Saint Joseph",
    "st. joseph": "Saint Joseph",
    "dekalb": "Dekalb",
    "la porte": "LaPorte",
    "laporte": "LaPorte",
    "la grange": "LaGrange",
    "lagrange": "LaGrange",
}


def _county_slug(county: str) -> str:
    return county.replace(" County", "").strip()


def _county_api_value(county: str) -> str:
    name = _county_slug(county)
    key = name.lower()
    if key in _COUNTY_API_KEY:
        return _COUNTY_API_KEY[key]
    # API uses title case county names (Gibson, Clark, …)
    return name.title() if name.lower() == name else name


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


def _http_client() -> httpx.Client:
    # audit.sboa.in.gov:8090 may present incomplete chain; verify=False for that host.
    return httpx.Client(
        timeout=60.0,
        follow_redirects=True,
        headers={"User-Agent": "ReClaw-SBOA-Ingest/1.0 (+public research; fair-report)"},
        verify=False,
    )


def search_filings(
    county: str,
    *,
    unit_types: list[str] | None = None,
    page_size: int = 50,
    years: list[int] | None = None,
) -> list[dict[str, Any]]:
    """POST filings/search — returns result rows for the county."""
    unit_types = unit_types or ["county"]
    body: dict[str, Any] = {
        "pageNumber": 1,
        "pageSize": page_size,
        "counties": [_county_api_value(county)],
        "unitTypes": unit_types,
        "sortColumn": "reportDate",
        "sortDescending": True,
    }
    if years:
        body["years"] = years

    with _http_client() as client:
        r = client.post(SBOA_API, json=body)
        r.raise_for_status()
        data = r.json()
    results = (data.get("data") or data).get("results") if isinstance(data.get("data"), dict) else data.get("results")
    if results is None and isinstance(data, dict):
        results = data.get("results") or []
    return list(results or [])


def _prefer_pdf_url(row: dict) -> str:
    """Return best first-try URL; download_pdf will try alternate hosts."""
    link = (row.get("pdfLink") or "").strip()
    if link:
        return link
    name = f"{row.get('reportNumber', 'report')}.pdf"
    return SBOA_PDF_IN_GOV.format(filename=name)


def _rank_row(row: dict) -> tuple:
    at = (row.get("auditType") or "").upper()
    pri = 99
    for k, v in _AUDIT_PRIORITY.items():
        if k in at:
            pri = v
            break
    # Special investigation report numbers often end with I
    rn = str(row.get("reportNumber") or "")
    if rn.upper().endswith("I"):
        pri = min(pri, 0)
    return (pri, -(row.get("id") or 0))


def discover_sboa_pdfs(county: str, *, limit: int = 40) -> dict:
    """
    Query live SBOA filings API for county unit audits.
    Caches manifest under data/cache/sboa/{county}/.
    """
    name = _county_slug(county)
    manifest = load_manifest(name)
    manifest["county"] = name
    manifest.setdefault("pdfs", [])
    manifest.setdefault("errors", [])
    manifest["sboa_index"] = SBOA_INDEX
    manifest["discovery"] = "filings_search_api"

    try:
        rows = search_filings(name, unit_types=["county"], page_size=max(limit, 50))
        # Also grab special investigation / towns if few county hits
        if len(rows) < 5:
            try:
                more = search_filings(name, unit_types=["county", "town", "city"], page_size=50)
                seen_ids = {r.get("id") for r in rows}
                for r in more:
                    if r.get("id") not in seen_ids:
                        rows.append(r)
            except Exception as e:
                manifest["errors"].append(f"expand_search: {e}")

        rows_sorted = sorted(rows, key=_rank_row)
        unique_pdfs: list[dict] = []
        seen_urls: set[str] = set()
        for row in rows_sorted:
            url = _prefer_pdf_url(row)
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            unique_pdfs.append(
                {
                    "url": url,
                    "filename": _pdf_name(url),
                    "report_number": row.get("reportNumber"),
                    "audit_type": row.get("auditType"),
                    "unit_name": row.get("unitName"),
                    "unit_type": row.get("unitType"),
                    "report_date": row.get("reportDate"),
                    "start_date": row.get("startDate"),
                    "end_date": row.get("endDate"),
                    "county_match": True,
                    "api_id": row.get("id"),
                }
            )
            if len(unique_pdfs) >= limit:
                break

        manifest["pdfs"] = unique_pdfs
        manifest["result_count"] = len(rows)
    except Exception as e:
        manifest["errors"].append(f"filings_search: {e}")
        # Fallback: Firecrawl only if explicitly available (may be out of credits)
        try:
            manifest = _discover_firecrawl_fallback(name, manifest, limit=limit)
        except Exception as e2:
            manifest["errors"].append(f"firecrawl_fallback: {e2}")

    _save_manifest(name, manifest)
    return manifest


def _discover_firecrawl_fallback(name: str, manifest: dict, *, limit: int) -> dict:
    from tools.firecrawl_discovery import map_site, _pdf_links

    links = map_site("https://www.in.gov/sboa/resources/reports/", limit=limit)
    county_links = [u for u in links if name.lower() in u.lower()]
    pdfs = _pdf_links(county_links) or _pdf_links(links)
    unique = []
    seen: set[str] = set()
    for url in pdfs:
        if url in seen:
            continue
        seen.add(url)
        unique.append({"url": url, "filename": _pdf_name(url), "county_match": name.lower() in url.lower()})
    if unique:
        manifest["pdfs"] = unique[:25]
        manifest["discovery"] = "firecrawl_fallback"
    return manifest


def download_pdf(url: str, dest: Path) -> Path:
    """Download PDF bytes to dest. Tries API link, then in.gov, then audit host."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fn = _pdf_name(url)
    urls: list[str] = []
    for u in (
        url,
        SBOA_PDF_IN_GOV.format(filename=fn),
        SBOA_PDF_AUDIT.format(filename=fn),
        f"https://audit.sboa.in.gov:8090/WebReports/{fn}",
    ):
        if u and u not in urls:
            urls.append(u)

    last_err: Exception | None = None
    with _http_client() as client:
        for u in urls:
            try:
                r = client.get(u)
                r.raise_for_status()
                if not r.content.startswith(b"%PDF"):
                    last_err = ValueError(f"not a pdf: {u} ct={r.headers.get('content-type')}")
                    continue
                dest.write_bytes(r.content)
                return dest
            except Exception as e:
                last_err = e
    raise RuntimeError(f"download failed for {url}: {last_err}")


def extract_text_from_pdf(path: Path, *, max_pages: int = 40) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for i, page in enumerate(reader.pages[:max_pages]):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        if t.strip():
            parts.append(f"[page {i + 1}]\n{t}")
    return "\n\n".join(parts)


_BOILERPLATE = re.compile(
    r"equal opportunity employer|state board of accounts\s+302 west|"
    r"telephone:\s*\(317\)|web site:\s*www\.in\.gov/sboa|"
    r"malfeasance,\s*misfeasance,\s*or nonfeasance|"  # stock legal blurb alone
    r"units are required to comply with all grant agreements",
    re.I,
)
_DOLLAR_RE = re.compile(r"\$\s*[\d,]+(?:\.\d{2})?")


def extract_findings_from_text(text: str, *, source: str, county: str, report_number: str | None = None) -> list[dict]:
    """Pull paragraph-level finding candidates from SBOA text.

    Prefers RESULTS AND COMMENTS sections and paragraphs with dollar amounts.
    Drops letterhead / stock legal boilerplate.
    """
    findings: list[dict] = []
    # Focus on results/comments body when present
    body = text
    m = re.search(
        r"(RESULTS AND COMMENTS|AUDIT RESULTS AND COMMENTS|COMMENT\s+AND\s+RECOMMENDATION)(.*)",
        text,
        re.I | re.S,
    )
    if m:
        body = m.group(0)

    for para in re.split(r"\n{2,}", body):
        para = re.sub(r"\s+", " ", para).strip()
        if len(para) < 80:
            continue
        if _BOILERPLATE.search(para) and not _DOLLAR_RE.search(para):
            continue
        if not _FINDING_PATTERNS.search(para) and not _DOLLAR_RE.search(para):
            continue
        # Require juice signal: $ amount OR strong finding word (not bare "compliance")
        strong = re.search(
            r"unsupported|overpayment|material weakness|significant deficiency|"
            r"special investigation|missing (deposit|fund|check)|personal (use|expense)|"
            r"credit card|nepotism|misappropriat|duplicate payment|questionable|"
            r"reimburse|charged to|responsible for",
            para,
            re.I,
        )
        has_money = bool(_DOLLAR_RE.search(para))
        if not strong and not has_money:
            continue

        page_m = re.search(r"\[page (\d+)\]", para)
        page = int(page_m.group(1)) if page_m else None
        if not page:
            idx = text.find(para[:80]) if len(para) > 80 else text.find(para)
            if idx > 0:
                prev = text[max(0, idx - 500) : idx]
                pm = list(re.finditer(r"\[page (\d+)\]", prev))
                if pm:
                    page = int(pm[-1].group(1))

        dollars = [d.replace(" ", "") for d in _DOLLAR_RE.findall(para)[:8]]
        findings.append(
            {
                "county": county,
                "excerpt": para[:600],
                "source": source,
                "report_number": report_number,
                "page": page,
                "amounts": dollars,
                "severity_hint": (
                    "high"
                    if strong
                    or re.search(r"material weakness|special investigation|unsupported|misappropriat", para, re.I)
                    else "medium"
                ),
            }
        )
        if len(findings) >= 20:
            break
    return findings


def ingest_sboa_county(
    county: str,
    *,
    discover: bool = True,
    download_top: int = 3,
    extract_pages: int = 40,
) -> dict:
    """
    Discover filings + download top PDFs + extract findings into manifest.

    Prefers SPECIAL INVESTIGATION then SUPPLEMENTAL compliance reports.
    """
    name = _county_slug(county)
    manifest = discover_sboa_pdfs(name) if discover else load_manifest(name)
    manifest.setdefault("errors", [])
    manifest.setdefault("local_pdfs", [])

    pdfs = list(manifest.get("pdfs") or [])
    # Sort again by audit type priority
    pdfs_sorted = sorted(
        pdfs,
        key=lambda p: _AUDIT_PRIORITY.get((p.get("audit_type") or "").upper(), 50),
    )

    all_findings: list[dict] = []
    local_pdfs: list[dict] = []
    cdir = cache_dir(name)

    for meta in pdfs_sorted[: max(1, download_top)]:
        url = meta.get("url")
        if not url:
            continue
        fn = meta.get("filename") or _pdf_name(url)
        dest = cdir / fn
        try:
            if not dest.exists() or dest.stat().st_size < 1000:
                download_pdf(url, dest)
            text = extract_text_from_pdf(dest, max_pages=extract_pages)
            text_path = cdir / (fn.rsplit(".", 1)[0] + ".txt")
            text_path.write_text(text[:200_000], encoding="utf-8")
            findings = extract_findings_from_text(
                text,
                source=url,
                county=name,
                report_number=meta.get("report_number"),
            )
            all_findings.extend(findings)
            local_pdfs.append(
                {
                    **meta,
                    "local_path": str(dest.relative_to(REPO_ROOT)),
                    "text_path": str(text_path.relative_to(REPO_ROOT)),
                    "bytes": dest.stat().st_size,
                    "findings_extracted": len(findings),
                }
            )
            if not manifest.get("excerpt") and text:
                manifest["excerpt"] = text[:4000]
                manifest["excerpt_source"] = url
        except Exception as e:
            manifest["errors"].append(f"pdf {fn}: {e}")

    # Dedupe findings by excerpt prefix
    seen_ex: set[str] = set()
    deduped: list[dict] = []
    for f in all_findings:
        key = (f.get("excerpt") or "")[:120]
        if key in seen_ex:
            continue
        seen_ex.add(key)
        deduped.append(f)

    # Prefer high severity + dollar amounts + named parties first
    def _find_rank(f: dict) -> tuple:
        ex = f.get("excerpt") or ""
        has_money = 0 if f.get("amounts") else 1
        named = 0 if re.search(r"\b(LLC|Inc\.|Sheriff|Commissioner|Enterprise)\b", ex) else 1
        sev = 0 if f.get("severity_hint") == "high" else 1
        return (sev, has_money, named)

    deduped.sort(key=_find_rank)

    manifest["findings"] = deduped[:25]
    manifest["local_pdfs"] = local_pdfs
    manifest["ingest_mode"] = "api_download_pypdf"
    _save_manifest(name, manifest)
    return manifest


def sboa_red_flags(county: str) -> list[RedFlag]:
    """Convert cached SBOA finding excerpts to RedFlags for red_flag_engine."""
    manifest = load_manifest(county)
    if not manifest.get("findings") and not manifest.get("pdfs"):
        return []

    flags: list[RedFlag] = []
    for i, finding in enumerate(manifest.get("findings", [])[:8]):
        rn = finding.get("report_number") or "SBOA"
        page = finding.get("page")
        page_s = f" p.{page}" if page else ""
        sev = finding.get("severity_hint") or ("high" if i < 2 else "medium")
        flags.append(
            RedFlag(
                severity=sev if sev in ("high", "medium", "low", "critical") else "medium",
                category="sboa_finding",
                description=(
                    f"SBOA {rn}{page_s} ({county}): {finding['excerpt'][:220]}…"
                ),
                evidence=json.dumps(
                    {
                        "source": finding.get("source"),
                        "type": "sboa_narrative",
                        "report_number": rn,
                        "page": page,
                        "county": county,
                    }
                ),
                recommended_action="Cite PDF page in script; link report in video description.",
            )
        )

    if not flags and manifest.get("pdfs"):
        top = manifest["pdfs"][0]
        flags.append(
            RedFlag(
                severity="medium",
                category="sboa_finding",
                description=(
                    f"{county} County: SBOA audit PDF on file — "
                    f"'{top.get('filename')}' report {top.get('report_number')} "
                    f"({top.get('audit_type')})"
                ),
                evidence=json.dumps(
                    {
                        "url": top.get("url"),
                        "type": "sboa_pdf_link",
                        "report_number": top.get("report_number"),
                    }
                ),
                recommended_action="Extract findings text for publishable hook.",
            )
        )
    return flags


if __name__ == "__main__":
    import argparse
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    ap = argparse.ArgumentParser(description="Ingest SBOA filings for an Indiana county")
    ap.add_argument("county", help="County name e.g. Clark")
    ap.add_argument("--download-top", type=int, default=3)
    ap.add_argument("--no-discover", action="store_true")
    args = ap.parse_args()
    m = ingest_sboa_county(args.county, discover=not args.no_discover, download_top=args.download_top)
    print(
        json.dumps(
            {
                "county": m.get("county"),
                "pdfs": len(m.get("pdfs") or []),
                "local_pdfs": len(m.get("local_pdfs") or []),
                "findings": len(m.get("findings") or []),
                "errors": m.get("errors"),
                "top_pdfs": [
                    {
                        "report": p.get("report_number"),
                        "type": p.get("audit_type"),
                        "url": p.get("url"),
                    }
                    for p in (m.get("pdfs") or [])[:5]
                ],
                "sample_finding": (m.get("findings") or [{}])[0].get("excerpt", "")[:200],
            },
            indent=2,
        )
    )

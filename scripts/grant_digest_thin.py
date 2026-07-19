#!/usr/bin/env python3
"""
Thin Path-C side offer: rural Indiana grant shortlist → markdown digest.

v0: pulls Grants.gov API search (public) + writes a draft digest under
    data/grant_digests/ pending human edit + send.

Does NOT auto-email or auto-apply. Human gate only.

Usage:
  PYTHONPATH=. .venv/bin/python scripts/grant_digest_thin.py
  PYTHONPATH=. .venv/bin/python scripts/grant_digest_thin.py --query "rural Indiana water" --limit 8
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "grant_digests"

# Public Grants.gov search2 (no API key)
SEARCH_URL = "https://api.grants.gov/v1/api/search2"


def search_grants(keyword: str, limit: int = 10) -> list[dict]:
    """Grants.gov search2. Returns list of opportunity hit dicts."""
    body = {
        "keyword": keyword,
        "oppStatuses": "posted",
        "rows": min(limit, 25),
        "startRecordNum": 0,
    }
    req = Request(
        SEARCH_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ReClaw-grant-digest/0.1 (research; human-reviewed)",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=45) as resp:
            raw = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        return [{"_error": str(exc), "_keyword": keyword}]

    if raw.get("errorcode") not in (0, "0", None) and raw.get("errorcode") != 0:
        return [{"_error": raw.get("msg") or str(raw.get("errorcode")), "_keyword": keyword}]

    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    hits = data.get("oppHits") or []
    if not isinstance(hits, list):
        return [{"_raw_keys": list(raw.keys())[:20], "_note": "unexpected API shape"}]
    return hits[:limit]


def row_from_hit(h: dict) -> dict:
    if h.get("_error") or h.get("_raw_keys"):
        return h
    title = h.get("title") or h.get("opportunityTitle") or "Untitled"
    agency = h.get("agency") or h.get("agencyName") or h.get("agencyCode") or ""
    opp_num = h.get("number") or h.get("opportunityNumber") or h.get("id") or ""
    close = h.get("closeDate") or h.get("closingDate") or ""
    hit_id = h.get("id") or ""
    link = h.get("opportunityLink") or h.get("url") or ""
    if not link and hit_id:
        link = f"https://www.grants.gov/search-results-detail/{hit_id}"
    elif not link and opp_num:
        link = f"https://www.grants.gov/search-results-detail/{opp_num}"
    return {
        "title": str(title)[:200],
        "agency": str(agency)[:120],
        "number": str(opp_num)[:80],
        "deadline": str(close)[:40],
        "link": str(link)[:300],
        "why_rural_in": "Review eligibility for rural IN towns / nonprofits / utilities",
    }


def render_markdown(rows: list[dict], *, week: str, query: str) -> str:
    lines = [
        f"# Indiana rural grant shortlist — week of {week}",
        "",
        f"_Draft only. Human must verify every link and deadline before sending._",
        f"_Query: `{query}` · Generated: {datetime.now(timezone.utc).isoformat()}_",
        "",
        "| # | Program | Agency | Deadline | Link | Why care |",
        "|---|---------|--------|----------|------|----------|",
    ]
    n = 0
    for r in rows:
        if r.get("_error"):
            lines.append(f"| — | API error | | | | `{r['_error'][:80]}` |")
            continue
        if r.get("_raw_keys"):
            lines.append(
                f"| — | Unexpected API shape | keys={r['_raw_keys']} | | | manual search grants.gov |"
            )
            continue
        n += 1
        title = (r.get("title") or "").replace("|", "/")
        agency = (r.get("agency") or "").replace("|", "/")
        deadline = (r.get("deadline") or "see link").replace("|", "/")
        link = r.get("link") or "https://www.grants.gov"
        why = r.get("why_rural_in") or ""
        lines.append(f"| {n} | {title} | {agency} | {deadline} | {link} | {why} |")

    lines += [
        "",
        "## Human checklist before send",
        "- [ ] Every deadline checked on source page",
        "- [ ] Eligibility fits rural IN (not coastal-only / metro-only)",
        "- [ ] No auto-apply; no guarantee of award",
        "- [ ] Disclaimer: not legal/financial advice",
        "",
        "## Offer blurb (optional footer)",
        "> Weekly shortlist for Indiana rural operators — 5–10 fits, links + deadlines. "
        "Pilot free for 2 weeks, then $49/mo. Reply to stay on the list.",
        "",
        "status: pending_approval",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Thin rural IN grant digest (draft only)")
    ap.add_argument(
        "--query",
        default="Indiana rural community water infrastructure",
        help="Grants.gov keyword search",
    )
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default data/grant_digests/YYYY-MM-DD-draft.md)",
    )
    args = ap.parse_args()

    week = date.today().isoformat()
    hits = search_grants(args.query, limit=args.limit)
    rows = [row_from_hit(h) for h in hits]
    if not rows:
        rows = [
            {
                "title": "Manual fill — Grants.gov search failed or empty",
                "agency": "",
                "deadline": "",
                "link": "https://www.grants.gov",
                "why_rural_in": "Operator: paste 5 real opportunities by hand this week",
            }
        ]

    md = render_markdown(rows, week=week, query=args.query)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = args.out or (OUT_DIR / f"{week}-draft.md")
    out.write_text(md, encoding="utf-8")
    print(f"Wrote {out}")
    print("Next: human edit → send to 3 pilot readers. Do not auto-email.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

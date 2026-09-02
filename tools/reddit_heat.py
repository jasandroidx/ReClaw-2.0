"""
Reddit heat signals for Indiana local-gov / utility outrage.

Why not www.reddit.com JSON from this host?
  Datacenter IPs get HTTP 403 "Blocked" / network security wall.
  Official OAuth API also 403 without residential IP or working app+token.

What works from Hetzner today:
  1) PullPush archive API (https://api.pullpush.io) — search submissions
  2) Reddit public RSS feeds (https://www.reddit.com/r/{sub}/.rss)

For full live Reddit API: create a script app at https://www.reddit.com/prefs/apps
  and set REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENT in .env,
  ideally with a non-datacenter exit (home Tailscale exit node or proxy).
"""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx

from tools.public_data_loaders import REPO_ROOT

CACHE = REPO_ROOT / "data" / "cache" / "heat" / "reddit"
PULLPUSH = "https://api.pullpush.io/reddit/search/submission/"
DEFAULT_SUBS = [
    "Indiana",
    "indianapolis",
    "evansville",
    "fortwayne",
    "southbend",
    "bloomington",
]
HEAT_TERMS = [
    "water rate",
    "rate hike",
    "sewer bill",
    "property tax",
    "SBOA",
    "audit",
    "county budget",
    "pothole",
    "utility bill",
    "tax increase",
    "commissioners",
]

_ATOM = {"a": "http://www.w3.org/2005/Atom"}


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": os.environ.get("REDDIT_USER_AGENT", "linux:reclaw-heat:v1.0")},
    )


def search_pullpush(
    query: str,
    *,
    subreddit: str | None = "Indiana",
    size: int = 25,
) -> list[dict[str, Any]]:
    """Search submissions via PullPush (works from datacenter)."""
    params: dict[str, Any] = {"q": query, "size": min(size, 100)}
    if subreddit:
        params["subreddit"] = subreddit
    with _client() as client:
        r = client.get(PULLPUSH, params=params)
        r.raise_for_status()
        data = r.json()
    rows = data.get("data") if isinstance(data, dict) else data
    out: list[dict[str, Any]] = []
    for row in rows or []:
        out.append(
            {
                "id": row.get("id"),
                "title": row.get("title"),
                "subreddit": row.get("subreddit"),
                "author": row.get("author"),
                "score": row.get("score"),
                "num_comments": row.get("num_comments"),
                "created_utc": row.get("created_utc"),
                "url": row.get("full_permalink")
                or row.get("url")
                or (f"https://www.reddit.com{row.get('permalink')}" if row.get("permalink") else None),
                "selftext": (row.get("selftext") or "")[:500],
                "source": "pullpush",
            }
        )
    return out


def fetch_subreddit_rss(subreddit: str, *, limit: int = 25) -> list[dict[str, Any]]:
    """Atom RSS for r/{sub} — often allowed when .json is blocked."""
    url = f"https://www.reddit.com/r/{subreddit}/.rss"
    with _client() as client:
        r = client.get(url)
        r.raise_for_status()
        raw = r.text
    root = ET.fromstring(raw)
    out: list[dict[str, Any]] = []
    for entry in root.findall("a:entry", _ATOM)[:limit]:
        title = (entry.findtext("a:title", default="", namespaces=_ATOM) or "").strip()
        link_el = entry.find("a:link", _ATOM)
        href = link_el.get("href") if link_el is not None else None
        updated = entry.findtext("a:updated", default="", namespaces=_ATOM)
        content = entry.findtext("a:content", default="", namespaces=_ATOM) or ""
        # strip rough HTML
        content = re.sub(r"<[^>]+>", " ", content)
        content = re.sub(r"\s+", " ", content).strip()[:500]
        author = entry.findtext("a:author/a:name", default="", namespaces=_ATOM)
        out.append(
            {
                "title": title,
                "url": href,
                "subreddit": subreddit,
                "author": author,
                "updated": updated,
                "selftext": content,
                "source": "reddit_rss",
            }
        )
    return out


def heat_watch(
    *,
    county: str | None = None,
    terms: list[str] | None = None,
    subreddits: list[str] | None = None,
    size: int = 15,
) -> dict[str, Any]:
    """
    Collect heat posts for Indiana local gov / utility keywords.
    Optionally bias query with county name.
    """
    terms = terms or HEAT_TERMS
    subreddits = subreddits or DEFAULT_SUBS[:3]
    hits: list[dict[str, Any]] = []
    errors: list[str] = []

    # Stay in Indiana-related subs — global search picks up Clark County NV, noise, etc.
    for term in terms[:8]:
        q = f'{term} "{county}"' if county else term
        try:
            hits.extend(search_pullpush(q, subreddit="Indiana", size=max(size // 2, 5)))
        except Exception as e:
            errors.append(f"pullpush Indiana '{term}': {e}")
        # Optional nearby city subs only (not global reddit)
        for sub in ("indianapolis", "evansville", "fortwayne"):
            if sub in (subreddits or []):
                try:
                    hits.extend(search_pullpush(q if county else term, subreddit=sub, size=3))
                except Exception as e:
                    errors.append(f"pullpush {sub} '{term}': {e}")

    for sub in subreddits:
        try:
            rss = fetch_subreddit_rss(sub, limit=10)
            # keep heat-ish titles only
            for row in rss:
                t = (row.get("title") or "").lower()
                if any(k.split()[0].lower() in t for k in terms) or any(
                    w in t for w in ("tax", "rate", "water", "audit", "county", "bill", "budget")
                ):
                    hits.append(row)
        except Exception as e:
            errors.append(f"rss {sub}: {e}")

    # Dedupe by title
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for h in hits:
        key = (h.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(h)

    # Score: prefer higher reddit score + keyword density
    def rank(h: dict) -> tuple:
        title = (h.get("title") or "").lower()
        kw = sum(1 for term in terms if term.split()[0].lower() in title)
        return (-(h.get("score") or 0), -kw)

    deduped.sort(key=rank)

    payload = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "county_bias": county,
        "count": len(deduped),
        "posts": deduped[:40],
        "errors": errors,
        "access_note": (
            "www.reddit.com JSON/API blocked from this datacenter (403). "
            "Using PullPush + RSS. For official API set REDDIT_* env + residential exit."
        ),
    }

    CACHE.mkdir(parents=True, exist_ok=True)
    slug = (county or "indiana").lower().replace(" ", "_")
    path = CACHE / f"heat_{slug}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["cache_path"] = str(path)
    return payload


def reddit_oauth_configured() -> bool:
    return bool(os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET"))


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--county", default="")
    ap.add_argument("--term", default="")
    args = ap.parse_args()
    if args.term:
        rows = search_pullpush(args.term, subreddit="Indiana", size=10)
        print(json.dumps(rows[:5], indent=2))
    else:
        print(json.dumps(heat_watch(county=args.county or None), indent=2)[:4000])

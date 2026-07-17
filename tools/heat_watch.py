"""
Unified heat / public-source watch for Story Factory.

Combines:
  - Reddit (PullPush + RSS) — tools/reddit_heat.py
  - SBOA cache if present — tools/sboa_ingest.py
  - Optional county bias

Facebook: not automated (see docs/ops/REDDIT-FACEBOOK-ACCESS.md).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.public_data_loaders import REPO_ROOT
from tools.reddit_heat import heat_watch as reddit_heat_watch
from tools.sboa_ingest import load_manifest

OUT = REPO_ROOT / "data" / "cache" / "heat"


def run_heat_watch(county: str | None = None) -> dict[str, Any]:
    reddit = reddit_heat_watch(county=county)
    sboa = {}
    if county:
        try:
            m = load_manifest(county)
            sboa = {
                "pdfs": len(m.get("pdfs") or []),
                "findings": len(m.get("findings") or []),
                "scraped_at": m.get("scraped_at"),
                "top_finding": (m.get("findings") or [{}])[0].get("excerpt", "")[:200],
            }
        except Exception as e:
            sboa = {"error": str(e)}

    out = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "county": county,
        "reddit": {
            "count": reddit.get("count"),
            "access_note": reddit.get("access_note"),
            "top_posts": (reddit.get("posts") or [])[:12],
            "errors": reddit.get("errors"),
        },
        "sboa_cache": sboa,
        "facebook": {
            "status": "not_automated",
            "note": "See docs/ops/REDDIT-FACEBOOK-ACCESS.md — needs Page token or manual paste",
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    slug = (county or "indiana").lower().replace(" ", "_")
    path = OUT / f"watch_{slug}.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    out["cache_path"] = str(path)
    return out


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--county", default="Clark")
    args = ap.parse_args()
    print(json.dumps(run_heat_watch(args.county or None), indent=2)[:5000])

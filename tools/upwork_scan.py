"""
Upwork job scanner for ReClaw — score jobs against your prefs, digests only.

Does NOT auto-apply or auto-message clients. Human gate always.

Backends:
  1. graphql — official Upwork GraphQL if UPWORK_ACCESS_TOKEN is set
  2. import  — JSON list of jobs (manual dump / future browser helper)
  3. demo    — sample jobs so you can test scoring without API

Usage:
  PYTHONPATH=. .venv/bin/python tools/upwork_scan.py
  PYTHONPATH=. .venv/bin/python tools/upwork_scan.py --demo
  PYTHONPATH=. .venv/bin/python tools/upwork_scan.py --import-json /tmp/jobs.json
  PYTHONPATH=. .venv/bin/python tools/upwork_scan.py --dry-run

Env:
  UPWORK_ACCESS_TOKEN  — OAuth bearer for GraphQL
  ALERT_WEBHOOK        — optional Discord/Telegram webhook for new hits
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREFS = ROOT / "data" / "upwork_preferences.yaml"
DIGEST_DIR = ROOT / "data" / "upwork_digests"
VAULT_LATEST = Path("/root/obsidian_vault/Ravenstack/ops/upwork-digest-latest.md")


@dataclass
class JobHit:
    job_id: str
    title: str
    description: str = ""
    url: str = ""
    budget_type: str = ""  # hourly | fixed | unknown
    budget_min: float | None = None
    budget_max: float | None = None
    experience: str = ""
    skills: list[str] = field(default_factory=list)
    client_spend: str = ""
    payment_verified: bool | None = None
    posted_at: str = ""
    query: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def text_blob(self) -> str:
        skills = " ".join(self.skills)
        return f"{self.title}\n{self.description}\n{skills}".lower()


@dataclass
class ScoredJob:
    job: JobHit
    score: float
    reasons: list[str]
    drops: list[str] = field(default_factory=list)

    @property
    def keep(self) -> bool:
        return not self.drops and self.score > 0


def load_prefs(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _money(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("$", "").strip()
    m = re.search(r"[\d.]+", s)
    return float(m.group(0)) if m else None


def score_job(job: JobHit, prefs: dict[str, Any]) -> ScoredJob:
    blob = job.text_blob()
    reasons: list[str] = []
    drops: list[str] = []
    score = 0.0

    for bad in prefs.get("exclude_if_any") or []:
        if str(bad).lower() in blob:
            drops.append(f"exclude:{bad}")

    must = [str(x).lower() for x in (prefs.get("must_include_any") or [])]
    if must and not any(m in blob for m in must):
        drops.append("missing_must_include")
    else:
        hits = [m for m in must if m in blob]
        if hits:
            score += 2.0 + 0.5 * min(len(hits), 6)
            reasons.append(f"must:{','.join(hits[:4])}")

    for nice in prefs.get("nice_to_have") or []:
        if str(nice).lower() in blob:
            score += 1.5
            reasons.append(f"nice:{nice}")

    budget = prefs.get("budget") or {}
    bmin = job.budget_min
    bmax = job.budget_max
    mid = None
    if bmin is not None and bmax is not None:
        mid = (bmin + bmax) / 2
    elif bmin is not None:
        mid = bmin
    elif bmax is not None:
        mid = bmax

    if job.budget_type == "hourly" and mid is not None:
        floor = budget.get("min_hourly")
        if floor is not None and mid < float(floor):
            drops.append(f"hourly_below_{floor}")
        pref = budget.get("prefer_hourly_min")
        if pref is not None and mid >= float(pref):
            score += 2.0
            reasons.append(f"hourly>={pref}")
    if job.budget_type == "fixed" and mid is not None:
        floor = budget.get("min_fixed")
        if floor is not None and mid < float(floor):
            drops.append(f"fixed_below_{floor}")
        pref = budget.get("prefer_fixed_min")
        if pref is not None and mid >= float(pref):
            score += 2.0
            reasons.append(f"fixed>={pref}")

    job_cfg = prefs.get("job") or {}
    exp = (job.experience or "").lower()
    for d in job_cfg.get("drop_experience") or []:
        if d and d.lower() in exp:
            drops.append(f"exp:{d}")
    for p in job_cfg.get("prefer_experience") or []:
        if p and p.lower() in exp:
            score += 1.0
            reasons.append(f"exp:{p}")

    client = prefs.get("client") or {}
    if client.get("prefer_payment_verified") and job.payment_verified is True:
        score += 1.0
        reasons.append("payment_verified")

    if not job.title.strip():
        drops.append("empty_title")

    return ScoredJob(job=job, score=round(score, 2), reasons=reasons, drops=drops)


def load_seen(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"ids": [], "meta": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ids": [], "meta": {}}


def save_seen(path: Path, seen: dict[str, Any], max_seen: int = 2000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ids = list(dict.fromkeys(seen.get("ids") or []))[-max_seen:]
    seen["ids"] = ids
    seen["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(seen, indent=2), encoding="utf-8")


# --- Backends -----------------------------------------------------------------


def fetch_demo(queries: list[str]) -> list[JobHit]:
    """Synthetic jobs so scoring/digest works without Upwork credentials."""
    samples = [
        JobHit(
            job_id="demo-001",
            title="Build multi-agent OpenClaw automation for ops digests",
            description=(
                "Need a Python engineer to wire OpenClaw + MCP tools for daily "
                "ops digests, Discord notify, and human approval gates. Self-hosted Docker."
            ),
            url="https://www.upwork.com/jobs/~demo001",
            budget_type="hourly",
            budget_min=45,
            budget_max=75,
            experience="expert",
            skills=["python", "docker", "ai agents"],
            payment_verified=True,
            query=queries[0] if queries else "demo",
        ),
        JobHit(
            job_id="demo-002",
            title="Shopify dropshipping product research VA",
            description="Find winning products for dropshipping store, onlyfans marketing optional.",
            url="https://www.upwork.com/jobs/~demo002",
            budget_type="hourly",
            budget_min=5,
            budget_max=10,
            experience="entry",
            skills=["shopify"],
            payment_verified=False,
            query="demo",
        ),
        JobHit(
            job_id="demo-003",
            title="n8n + FastAPI integration for lead enrichment",
            description="Connect n8n workflows to a FastAPI service, scrape public data, score leads.",
            url="https://www.upwork.com/jobs/~demo003",
            budget_type="fixed",
            budget_min=800,
            budget_max=1500,
            experience="intermediate",
            skills=["n8n", "python", "fastapi"],
            payment_verified=True,
            query=queries[0] if queries else "demo",
        ),
    ]
    return samples


def fetch_import(path: Path) -> list[JobHit]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("jobs") or data.get("items") or []
    out: list[JobHit] = []
    for i, row in enumerate(items):
        if not isinstance(row, dict):
            continue
        jid = str(row.get("id") or row.get("job_id") or row.get("ciphertext") or f"import-{i}")
        out.append(
            JobHit(
                job_id=jid,
                title=str(row.get("title") or ""),
                description=str(row.get("description") or row.get("snippet") or ""),
                url=str(row.get("url") or row.get("link") or f"https://www.upwork.com/jobs/{jid}"),
                budget_type=str(row.get("budget_type") or row.get("type") or "unknown"),
                budget_min=_money(row.get("budget_min") or row.get("amount") or row.get("hourly_min")),
                budget_max=_money(row.get("budget_max") or row.get("hourly_max")),
                experience=str(row.get("experience") or row.get("contractor_tier") or ""),
                skills=[str(s) for s in (row.get("skills") or [])],
                client_spend=str(row.get("client_spend") or ""),
                payment_verified=row.get("payment_verified"),
                posted_at=str(row.get("posted_at") or row.get("created") or ""),
                query=str(row.get("query") or "import"),
                raw=row,
            )
        )
    return out


def fetch_graphql(prefs: dict[str, Any], queries: list[str]) -> list[JobHit]:
    """
    Official GraphQL job search. Requires UPWORK_ACCESS_TOKEN.

    Register an app: https://www.upwork.com/developer/
    Docs: https://www.upwork.com/developer/documentation/graphql/api/docs/index.html
    """
    token = os.environ.get("UPWORK_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("UPWORK_ACCESS_TOKEN not set")

    gcfg = prefs.get("graphql") or {}
    endpoint = gcfg.get("endpoint") or "https://api.upwork.com/graphql"
    page_size = int(gcfg.get("page_size") or 20)
    search_type = gcfg.get("search_type") or "USER_JOBS_SEARCH"

    # Minimal query — field names evolve; we tolerate partial responses.
    gql = """
    query marketplaceJobPostingsSearch(
      $marketPlaceJobFilter: MarketplaceJobPostingsSearchFilter
      $searchType: MarketplaceJobPostingSearchType
      $sortAttributes: [MarketplaceJobPostingSearchSortAttribute]
    ) {
      marketplaceJobPostingsSearch(
        marketPlaceJobFilter: $marketPlaceJobFilter
        searchType: $searchType
        sortAttributes: $sortAttributes
      ) {
        totalCount
        edges {
          node {
            id
            title
            description
            ciphertext
            createdDateTime
            experienceLevel
            hourlyBudgetMin
            hourlyBudgetMax
            amount { amount currency }
          }
        }
      }
    }
    """

    jobs: list[JobHit] = []
    errors: list[str] = []

    for q in queries:
        variables = {
            "marketPlaceJobFilter": {
                "searchExpression_eq": {"andOpenSearch": q},
                "pagination_eq": {"first": page_size, "after": "0"},
            },
            "searchType": search_type,
            "sortAttributes": [{"field": "RECENCY"}],
        }
        # Fallback filter shapes if API rejects first form
        alt_filters = [
            variables,
            {
                "marketPlaceJobFilter": {
                    "titleExpression_eq": q,
                    "pagination_eq": {"first": page_size, "after": "0"},
                },
                "searchType": search_type,
                "sortAttributes": [{"field": "RECENCY"}],
            },
        ]

        payload = None
        last_err = ""
        for vars_try in alt_filters:
            body = json.dumps({"query": gql, "variables": vars_try}).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "ReClaw-UpworkScan/0.1",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    payload = json.loads(resp.read().decode("utf-8", errors="replace"))
                if payload.get("errors"):
                    last_err = json.dumps(payload["errors"])[:300]
                    payload = None
                    continue
                break
            except urllib.error.HTTPError as exc:
                last_err = f"HTTP {exc.code}: {exc.read()[:200]!r}"
                payload = None
            except Exception as exc:  # noqa: BLE001
                last_err = str(exc)
                payload = None

        if payload is None:
            errors.append(f"query={q!r}: {last_err}")
            continue

        data = (payload.get("data") or {}).get("marketplaceJobPostingsSearch") or {}
        edges = data.get("edges") or []
        for edge in edges:
            node = (edge or {}).get("node") or {}
            jid = str(node.get("id") or node.get("ciphertext") or "")
            if not jid:
                continue
            amount = node.get("amount") or {}
            fixed = _money(amount.get("amount") if isinstance(amount, dict) else None)
            hmin = _money(node.get("hourlyBudgetMin"))
            hmax = _money(node.get("hourlyBudgetMax"))
            if hmin is not None or hmax is not None:
                btype, bmin, bmax = "hourly", hmin, hmax
            elif fixed is not None:
                btype, bmin, bmax = "fixed", fixed, fixed
            else:
                btype, bmin, bmax = "unknown", None, None
            cipher = node.get("ciphertext") or jid
            jobs.append(
                JobHit(
                    job_id=jid,
                    title=str(node.get("title") or ""),
                    description=str(node.get("description") or "")[:4000],
                    url=f"https://www.upwork.com/jobs/{cipher}",
                    budget_type=btype,
                    budget_min=bmin,
                    budget_max=bmax,
                    experience=str(node.get("experienceLevel") or ""),
                    posted_at=str(node.get("createdDateTime") or ""),
                    query=q,
                    raw=node,
                )
            )

    if not jobs and errors:
        raise RuntimeError("GraphQL failed: " + " | ".join(errors[:3]))
    return jobs


def collect_jobs(
    prefs: dict[str, Any],
    *,
    force_demo: bool = False,
    import_json: Path | None = None,
) -> tuple[list[JobHit], str]:
    queries = list(prefs.get("queries") or ["python automation"])
    if force_demo:
        return fetch_demo(queries), "demo"
    if import_json:
        return fetch_import(import_json), "import"

    preferred = (prefs.get("backends") or {}).get("preferred") or ["graphql", "import", "demo"]
    last_err = ""
    for name in preferred:
        try:
            if name == "graphql" and os.environ.get("UPWORK_ACCESS_TOKEN"):
                return fetch_graphql(prefs, queries), "graphql"
            if name == "demo":
                return fetch_demo(queries), "demo"
        except Exception as exc:  # noqa: BLE001
            last_err = f"{name}: {exc}"
            continue

    # No token → demo so the pipeline still proves scoring works
    jobs = fetch_demo(queries)
    note = "demo (set UPWORK_ACCESS_TOKEN for live GraphQL"
    if last_err:
        note += f"; last error: {last_err}"
    note += ")"
    return jobs, note


# --- Output -------------------------------------------------------------------


def render_digest(
    scored: list[ScoredJob],
    *,
    backend: str,
    prefs_path: Path,
    new_only_count: int,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Upwork digest — {now}",
        "",
        f"_Backend: `{backend}` · Prefs: `{prefs_path}` · New matches: **{new_only_count}**_",
        "",
        "Human only: open links and apply yourself. This tool never proposals.",
        "",
    ]
    if not scored:
        lines += [
            "## No matching new jobs",
            "",
            "- Check `data/upwork_preferences.yaml` keywords",
            "- Or set `UPWORK_ACCESS_TOKEN` for live GraphQL search",
            "- Or run with `--import-json jobs.json`",
            "",
        ]
        return "\n".join(lines)

    lines += [
        "| Score | Title | Budget | Why | Link |",
        "|------:|-------|--------|-----|------|",
    ]
    for s in scored:
        j = s.job
        if j.budget_type == "hourly" and (j.budget_min or j.budget_max):
            bud = f"${j.budget_min or '?'}-${j.budget_max or '?'}/hr"
        elif j.budget_min:
            bud = f"${j.budget_min:,.0f} fixed"
        else:
            bud = j.budget_type or "?"
        title = (j.title or "").replace("|", "/")[:80]
        why = ", ".join(s.reasons[:4]).replace("|", "/")
        link = j.url or ""
        lines.append(f"| {s.score:.1f} | {title} | {bud} | {why} | {link} |")

    lines += ["", "## Details", ""]
    for s in scored:
        j = s.job
        lines.append(f"### [{s.score:.1f}] {j.title}")
        lines.append(f"- Link: {j.url}")
        lines.append(f"- Query: `{j.query}` · Exp: {j.experience or 'n/a'}")
        lines.append(f"- Reasons: {', '.join(s.reasons)}")
        snip = (j.description or "").strip().replace("\n", " ")
        if snip:
            lines.append(f"- Snippet: {snip[:280]}…")
        lines.append("")

    lines += [
        "---",
        "Edit prefs: `data/upwork_preferences.yaml`",
        "Re-run: `PYTHONPATH=. .venv/bin/python tools/upwork_scan.py`",
        "",
    ]
    return "\n".join(lines)


def maybe_webhook(text: str, n_new: int) -> None:
    if n_new <= 0:
        return
    url = os.environ.get("ALERT_WEBHOOK", "").strip()
    if not url or "example.com" in url:
        return
    # Discord-friendly
    content = f"**Upwork digest:** {n_new} new matching job(s)\n```\n{text[:1500]}\n```"
    body = json.dumps({"content": content[:1900]}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "ReClaw-UpworkScan/0.1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except Exception as exc:  # noqa: BLE001
        print(f"webhook failed: {exc}", file=sys.stderr)


def run(
    prefs_path: Path,
    *,
    force_demo: bool = False,
    import_json: Path | None = None,
    dry_run: bool = False,
    mark_seen: bool = True,
) -> int:
    prefs = load_prefs(prefs_path)
    if not prefs.get("enabled", True):
        print("upwork scan disabled in preferences")
        return 0

    jobs, backend = collect_jobs(prefs, force_demo=force_demo, import_json=import_json)
    scored_all = [score_job(j, prefs) for j in jobs]
    kept = [s for s in scored_all if s.keep]
    kept.sort(key=lambda s: (-s.score, s.job.title))

    seen_path = ROOT / (prefs.get("seen_path") or "data/cache/upwork/seen_jobs.json")
    seen = load_seen(seen_path)
    seen_ids = set(seen.get("ids") or [])
    only_new = (prefs.get("notify") or {}).get("only_new", True)

    fresh = []
    for s in kept:
        if only_new and s.job.job_id in seen_ids:
            continue
        fresh.append(s)

    max_n = int((prefs.get("notify") or {}).get("max_jobs_in_digest") or 15)
    fresh = fresh[:max_n]

    digest = render_digest(
        fresh,
        backend=backend,
        prefs_path=prefs_path,
        new_only_count=len(fresh),
    )
    print(digest)

    if dry_run:
        return 0

    notify = prefs.get("notify") or {}
    if notify.get("write_digest", True):
        DIGEST_DIR.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out = DIGEST_DIR / f"{day}.md"
        out.write_text(digest, encoding="utf-8")
        print(f"\nWrote {out}", file=sys.stderr)

    if notify.get("write_vault_copy", True):
        try:
            VAULT_LATEST.parent.mkdir(parents=True, exist_ok=True)
            VAULT_LATEST.write_text(digest, encoding="utf-8")
            print(f"Wrote {VAULT_LATEST}", file=sys.stderr)
        except OSError as exc:
            print(f"vault copy skipped: {exc}", file=sys.stderr)

    if notify.get("webhook", True):
        maybe_webhook(digest, len(fresh))

    if mark_seen and fresh:
        for s in fresh:
            seen_ids.add(s.job.job_id)
        seen["ids"] = list(seen_ids)
        save_seen(seen_path, seen, max_seen=int(prefs.get("max_seen") or 2000))

    # Machine summary for cron logs
    print(
        json.dumps(
            {
                "backend": backend,
                "fetched": len(jobs),
                "kept": len(kept),
                "new": len(fresh),
                "dropped": len(scored_all) - len(kept),
            }
        ),
        file=sys.stderr,
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Scan Upwork for preferred jobs → digest")
    ap.add_argument("--prefs", type=Path, default=DEFAULT_PREFS)
    ap.add_argument("--demo", action="store_true", help="Force demo backend")
    ap.add_argument("--import-json", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true", help="Print only; no write/seen")
    ap.add_argument("--no-mark-seen", action="store_true")
    args = ap.parse_args()
    return run(
        args.prefs,
        force_demo=args.demo,
        import_json=args.import_json,
        dry_run=args.dry_run,
        mark_seen=not args.no_mark_seen,
    )


if __name__ == "__main__":
    sys.exit(main())

"""
Dual-receipt pilot — Story Factory offline package builder.

Builds ONE publishable story with:
  - pain_leg  (local news / lived impact)
  - money_leg (public $ / rate / fund / SBOA)
  - ClaimGate checklist (actor, exact $, contrast, receipt)

Does NOT unfreeze the county mill. Human must review the card.

Usage:
  PYTHONPATH=. .venv/bin/python tools/dual_receipt_pilot.py winslow-water
  PYTHONPATH=. .venv/bin/python tools/dual_receipt_pilot.py winslow-water --write-vault
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.claim_gate import ClaimObject, evaluate_claim

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "dual_receipt_pilots"
VAULT_RURAL = Path("/root/obsidian_vault/Rural Data")
OUTBOX = Path("/root/outbox")

# Pilot stories — fair-report only; all facts sourced from filed news/public records.
# Winslow water: 14News WFIE 2025-01-14 + 2025-01-16 (scraped 2026-07-22).
PILOTS: dict[str, dict[str, Any]] = {
    "winslow-water": {
        "id": "dual-winslow-water-2025-01",
        "place": "Winslow, Indiana",
        "county": "Pike",
        "area": "Winslow",
        "template": "bill_shock_dual_receipt",
        "heat_rank": "2_bill_shock",
        "pain_leg": {
            "source": "local_news",
            "summary": (
                "Explosive town hall; residents angry/confused over proposed water and sewer "
                "rate hikes; fixed-income fear; 'this town needs to get it together.'"
            ),
            "quotes": [
                "When you jump it from 3% to 42% or 54%, that's scary for people… especially on a fixed budget.",
                "This town needs to get it together.",
            ],
            "urls": [
                "https://www.14news.com/2025/01/14/neighbors-voice-their-anger-over-proposed-water-rate-hike-winslow/",
                "https://www.14news.com/2025/01/16/this-town-needs-get-it-together-winslow-residents-left-questions-after-explosive-town-hall-meeting/",
            ],
        },
        "money_leg": {
            "source": "local_news_official_meeting",
            "summary": (
                "Proposed ~45% water rate increase and ~10% sewer increase; council cites aging "
                "water system repairs. Resident/former council president analysis: many minimum-use "
                "customers (~2,000 gal) see about a $13 monthly bump."
            ),
            "exact_dollar": "$13",
            "contrast": "45% water / 10% sewer proposed vs prior ~3% expectations; peer-size bill concern",
            "actor": "Winslow Town Council",
            "actor_type": "place_utility",
            "urls": [
                "https://www.14news.com/2025/01/14/neighbors-voice-their-anger-over-proposed-water-rate-hike-winslow/",
                "https://www.14news.com/2025/01/16/this-town-needs-get-it-together-winslow-residents-left-questions-after-explosive-town-hall-meeting/",
                "https://www.tristatehomepage.com/news/water-rates-proposed-to-increase-by-nearly-50-in-winslow/",
            ],
        },
        "legal": {
            "mode": "fair_report",
            "attribution": "According to 14News (WFIE) reporting on Winslow town council meetings, January 2025.",
            "forbidden": ["fraud", "embezzled", "stole", "corrupt", "criminal"],
            "note": "Rate ordinance / council proceeding — no criminal imputation.",
        },
        "hook_options": [
            (
                "Did you know Winslow, Indiana proposed a 45% water rate hike — about $13 more a month "
                "for many minimum users — while residents at a packed town hall said people on fixed "
                "budgets are scared? (14News, Jan 2025)"
            ),
            (
                "Did you know a small Indiana town hall erupted over a jump from ~3% expectations to "
                "a proposed 42–54% water bill shock — with a second reading set after the shouting? "
                "(14News, Winslow)"
            ),
        ],
        "script_60s": {
            "0_03": "Did you know Winslow, Indiana floated a ~45% water rate hike?",
            "0_15": (
                "14News covered the town hall: 45% water, 10% sewer. Council said aging pipes and repairs. "
                "Residents said fixed budgets can't absorb a jump like that."
            ),
            "0_35": (
                "A former council president who pulled documents said many low-use homes might see "
                "about $13 more a month — small on paper, dealbreaker for some."
            ),
            "0_50": "Fair report of public meetings and news — not an accusation of crime.",
            "0_60": "Follow for more Indiana public-record stories. Sources in description.",
        },
    },
}


def _synthetic_flag(pilot: dict[str, Any]) -> Any:
    """Minimal flag-like object for ClaimGate."""

    class F:
        pass

    f = F()
    m = pilot["money_leg"]
    p = pilot["pain_leg"]
    f.category = "rate_shock"
    f.description = (
        f"{m.get('actor')}: proposed water rate increase ~45% / sewer ~10% in {pilot['place']}. "
        f"Many minimum-use customers ~{m.get('exact_dollar')} monthly bump. "
        f"Contrast: {m.get('contrast')}. "
        f"Pain: {p.get('summary')[:180]}"
    )
    f.evidence = {
        "actor": m.get("actor"),
        "actor_type": m.get("actor_type"),
        "amount": 13,
        "exact_dollar": m.get("exact_dollar"),
        "contrast": m.get("contrast"),
        "url": (m.get("urls") or [""])[0],
        "source": "14News WFIE town council coverage",
        "source_url": (m.get("urls") or [""])[0],
    }
    f.recommended_action = "Human review dual-receipt card; fair-report only."
    f.severity = "high"
    return f


def build_pilot(name: str) -> dict[str, Any]:
    if name not in PILOTS:
        raise SystemExit(f"Unknown pilot {name!r}. Choose: {', '.join(PILOTS)}")
    pilot = PILOTS[name]
    flag = _synthetic_flag(pilot)
    result = evaluate_claim(flag, county=pilot["county"])
    package = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pilot_id": pilot["id"],
        "place": pilot["place"],
        "county": pilot["county"],
        "area": pilot["area"],
        "template": pilot["template"],
        "heat_rank": pilot["heat_rank"],
        "pain_leg": pilot["pain_leg"],
        "money_leg": pilot["money_leg"],
        "legal": pilot["legal"],
        "hook_options": pilot["hook_options"],
        "script_60s": pilot["script_60s"],
        "claim_gate": result.to_dict(),
        "claim_gate_ok": result.ok,
        "human_gate": "pending_approval",
        "do_not": [
            "auto-publish",
            "unfreeze county mill",
            "invent criminal intent",
            "use Gateway AFR ent_name as vendor",
        ],
    }
    return package


def write_outputs(package: dict[str, Any], *, write_vault: bool, write_outbox: bool) -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = package["pilot_id"]
    paths: list[Path] = []
    jp = OUT_DIR / f"{stem}.json"
    jp.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    paths.append(jp)

    md = _render_md(package)
    mp = OUT_DIR / f"{stem}.md"
    mp.write_text(md, encoding="utf-8")
    paths.append(mp)

    if write_vault and VAULT_RURAL.is_dir():
        vp = VAULT_RURAL / f"{datetime.now(timezone.utc).date()}-dual-receipt-{package['area'].lower()}.md"
        vp.write_text(md, encoding="utf-8")
        paths.append(vp)
        vj = VAULT_RURAL / f"{datetime.now(timezone.utc).date()}-dual-receipt-{package['area'].lower()}.json"
        vj.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
        paths.append(vj)

    if write_outbox and OUTBOX.is_dir():
        op = OUTBOX / f"DUAL-RECEIPT-{package['area'].upper()}.md"
        op.write_text(md, encoding="utf-8")
        paths.append(op)
        # simple html
        html = f"""<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Dual-receipt: {package['place']}</title>
<style>body{{font-family:system-ui;max-width:44rem;margin:2rem auto;padding:0 1rem;background:#0b1020;color:#e8f0ff;line-height:1.5}}
pre{{white-space:pre-wrap;background:#132038;padding:1rem;border-radius:8px}}a{{color:#5ec8ff}}</style></head>
<body><h1>Dual-receipt pilot — {package['place']}</h1>
<p>ClaimGate: <strong>{'PASS' if package.get('claim_gate_ok') else 'FAIL'}</strong> · Human gate: pending</p>
<pre>{md.replace('&','&amp;').replace('<','&lt;')}</pre>
<p><a href="/">← Outbox</a></p></body></html>"""
        oh = OUTBOX / f"DUAL-RECEIPT-{package['area'].upper()}.html"
        oh.write_text(html, encoding="utf-8")
        paths.append(oh)

    return paths


def _render_md(package: dict[str, Any]) -> str:
    cg = package.get("claim_gate") or {}
    claim = (cg.get("claim") or {}) if isinstance(cg, dict) else {}
    missing = claim.get("missing") or []
    lines = [
        f"# Dual-receipt pilot — {package['place']}",
        "",
        f"**Pilot ID:** `{package['pilot_id']}`  ",
        f"**County/area:** {package['county']} / {package['area']}  ",
        f"**Heat:** {package.get('heat_rank')}  ",
        f"**ClaimGate:** {'PASS' if package.get('claim_gate_ok') else 'FAIL'}  ",
        f"**Human gate:** `{package.get('human_gate')}`  ",
        f"**Generated:** {package.get('generated_at')}",
        "",
        "## ClaimGate fields",
        f"- Actor: {claim.get('actor') or '—'} ({claim.get('actor_type') or '—'})",
        f"- Exact $: {claim.get('exact_dollar') or '—'}",
        f"- Contrast: {claim.get('contrast') or '—'}",
        f"- Receipt: {claim.get('receipt_path') or '—'}",
        f"- Missing: {', '.join(missing) if missing else 'none'}",
        "",
        "## Pain leg (local impact)",
        package["pain_leg"]["summary"],
        "",
        "Sources:",
    ]
    for u in package["pain_leg"].get("urls") or []:
        lines.append(f"- {u}")
    lines += ["", "## Money leg (public $ / rate)", package["money_leg"]["summary"], "", "Sources:"]
    for u in package["money_leg"].get("urls") or []:
        lines.append(f"- {u}")
    lines += ["", "## Legal", package["legal"]["attribution"], f"Mode: {package['legal']['mode']}", ""]
    lines += ["## Hook options (pick one)"]
    for i, h in enumerate(package.get("hook_options") or [], 1):
        lines.append(f"{i}. {h}")
    lines += ["", "## 60s script skeleton"]
    for k, v in (package.get("script_60s") or {}).items():
        lines.append(f"- **{k}:** {v}")
    lines += [
        "",
        "## Do not",
        *[f"- {x}" for x in package.get("do_not") or []],
        "",
        "## Operator next",
        "1. Read ClaimGate missing fields — fix sources if FAIL.",
        "2. If you would post this short, approve for production script polish.",
        "3. Do **not** unfreeze county mill until 1–3 dual-receipt cards pass your personal bar.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Build dual-receipt Story Factory pilot package")
    ap.add_argument("pilot", nargs="?", default="winslow-water", help="Pilot key (default winslow-water)")
    ap.add_argument("--list", action="store_true", help="List pilots")
    ap.add_argument("--write-vault", action="store_true", help="Write to Obsidian Rural Data/")
    ap.add_argument("--write-outbox", action="store_true", default=True, help="Write to permanent outbox")
    ap.add_argument("--no-outbox", action="store_true")
    args = ap.parse_args()
    if args.list:
        print("\n".join(PILOTS))
        return
    write_outbox = args.write_outbox and not args.no_outbox
    package = build_pilot(args.pilot)
    paths = write_outputs(package, write_vault=args.write_vault, write_outbox=write_outbox)
    print(json.dumps({"claim_gate_ok": package["claim_gate_ok"], "paths": [str(p) for p in paths]}, indent=2))
    if not package["claim_gate_ok"]:
        print("ClaimGate FAIL — see missing fields in package", flush=True)


if __name__ == "__main__":
    main()

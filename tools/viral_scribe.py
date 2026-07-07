"""
Viral Scribe — HHVCTA short-form script manifests from red-flag JSON.

Transforms anomaly reports into TikTok/Reels/Shorts JSON with:
  hook_text, script_body (scenes), on_screen_text, visual_directives

Fair-report guardrails: high-retention questions and patterns — not crime allegations.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from tools.public_data_loaders import REPO_ROOT
from tools.viral_hooks import (
    _flag_get,
    build_viral_hook,
    classify_flag,
    extract_hook_context,
    get_playbook_visual,
    load_playbook,
    sanitize_hook,
)

DIRECTIVE_PATH = REPO_ROOT / "data" / "viral_scribe_directive.yaml"
DISCLAIMER = (
    "Patterns in public financial records only. Not an allegation of crime or wrongdoing."
)

_BLOCKED_RE = re.compile(
    r"\b("
    r"caught|exposed|hid|corrupt|criminal|guilty|stole|stealing|fraudster|"
    r"faking|fake numbers|embezzle|busted|scamming|scammer|back door"
    r")\b",
    re.I,
)


@lru_cache(maxsize=1)
def load_directive() -> dict[str, Any]:
    if not DIRECTIVE_PATH.is_file():
        return {}
    return yaml.safe_load(DIRECTIVE_PATH.read_text(encoding="utf-8")) or {}


def _scribe_key(flag: Any) -> str:
    """Map flag to emotional_filters key in directive YAML."""
    pb_key = classify_flag(flag)
    mapping = {
        "smurfing": "smurfing",
        "round_number": "round_number",
        "weekend_drop": "weekend_drop",
        "duplicate_payment": "duplicate_payment",
        "salary_shock": "salary_shock",
        "benford": "benford",
    }
    if pb_key and pb_key in mapping:
        return mapping[pb_key]
    cat = _flag_get(flag, "category", "") or ""
    if "benford" in cat:
        return "benford"
    if cat == "split_purchase":
        return "smurfing"
    if cat == "round_number_cluster":
        return "round_number"
    if cat in ("double_dip", "statistical_anomaly"):
        return "duplicate_payment"
    if cat == "salary_shock":
        return "salary_shock"
    return "generic"


def _format_tpl(template: str, ctx: dict[str, Any]) -> str:
    class _Safe(dict):
        def __missing__(self, k: str) -> str:
            return "{" + k + "}"

    try:
        return template.format_map(_Safe(ctx))
    except Exception:
        return template


def _sanitize_script(text: str) -> str:
    out = _BLOCKED_RE.sub("", text or "")
    out = re.sub(r"\s{2,}", " ", out).strip()
    out = out.replace("literally faking the numbers", "digits that don't look natural")
    out = out.replace("Ghost Invoices", "round-dollar patterns")
    return out


def _pick_template(templates: list[str], seed: str) -> str:
    if not templates:
        return ""
    idx = sum(ord(c) for c in seed) % len(templates)
    return templates[idx]


def _build_hint(ctx: dict[str, Any], key: str) -> str:
    d = load_directive()
    tpl = _pick_template(d.get("hint_templates") or [], key)
    return _sanitize_script(tpl)


def _build_value(flag: Any, ctx: dict[str, Any], key: str) -> str:
    d = load_directive()
    filt = (d.get("emotional_filters") or {}).get(key) or {}
    eli5 = filt.get("eli5", "").strip()
    desc = _flag_get(flag, "description", "") or ""
    parts = [eli5] if eli5 else []
    if desc:
        parts.append(f"The flagged line: {desc}")
    parts.append("Could be innocent — but it's public money and the explanation should be on the record.")
    return _sanitize_script(" ".join(parts))


def _build_credibility(place: str, source: str, key: str) -> str:
    d = load_directive()
    tpl = _pick_template(d.get("credibility_templates") or [], key + source)
    return _sanitize_script(_format_tpl(tpl, {"place": place, "source": source}))


def _build_takeaway(ctx: dict[str, Any], key: str) -> str:
    d = load_directive()
    filt = (d.get("emotional_filters") or {}).get(key) or {}
    tpl = filt.get("takeaway_tpl") or "It's your tax money. Fair questions deserve answers."
    return _sanitize_script(_format_tpl(tpl, ctx))


def _build_action(place: str, key: str) -> str:
    d = load_directive()
    tpl = _pick_template(d.get("action_templates") or [], key)
    return _sanitize_script(_format_tpl(tpl, {"place": place}))


def _on_screen_bursts(key: str, ctx: dict[str, Any], beat: str) -> list[str]:
    d = load_directive()
    filt = (d.get("emotional_filters") or {}).get(key) or {}
    base = list(filt.get("on_screen") or ["PUBLIC RECORD", "YOUR MONEY"])
    if beat == "hook" and ctx.get("amount_fmt"):
        return [str(ctx.get("amount_fmt")).upper().replace("$", ""), base[0]][:3]
    if beat == "hint":
        return ["PATTERN FOUND", "CHECK THIS", "PUBLIC DATA"][:3]
    if beat == "credibility":
        return ["SOURCE", "VERIFY IT", (ctx.get("place") or "COUNTY").upper()][:3]
    if beat == "action":
        return ["TAG THEM", "SHARE", "YOUR COUNTY"][:3]
    return base[:3]


def _visual_directives(key: str, beat: str, flag: Any) -> list[str]:
    pb_vis = get_playbook_visual(flag)
    d = load_directive()
    filt = (d.get("emotional_filters") or {}).get(key) or {}
    theme_visuals = list(filt.get("visuals") or [])

    if beat == "hook":
        out = []
        if pb_vis.get("visual_asset"):
            out.append(f"Show {pb_vis['visual_asset']}")
        if pb_vis.get("text_overlay"):
            out.append(f"Flash on-screen: {pb_vis['text_overlay']}")
        out.extend(theme_visuals[:2])
        return out[:4] or ["Courthouse b-roll, darken 40%"]

    if beat == "value":
        vendor = extract_hook_context(flag, "").get("vendor")
        if vendor:
            return [f"Highlight vendor '{vendor}'", "Bar chart spike", "Scroll raw data table"][:4]
        return ["Dynamic chart render", "Zoom flagged amount", "Source row highlight"][:4]

    if beat == "credibility":
        return ["Screenshot open data portal", "Highlight source URL", "Show export timestamp"][:3]

    if beat == "action":
        return ["CTA subscribe card", "Comment prompt overlay", "Red border pulse"][:3]

    return theme_visuals[:2] or ["Subtle camera push"]


def build_scribe_manifest(
    flag: Any,
    *,
    county: str,
    source: str = "Indiana Gateway public records",
    review_id: str | None = None,
) -> dict[str, Any]:
    """
    Full Viral Scribe JSON manifest from a RedFlag or anomaly dict.

    Output fields per system directive:
      hook_text, script_body, on_screen_text (per scene), visual_directives (per scene)
    """
    ctx = extract_hook_context(flag, county)
    place = ctx["place"]
    key = _scribe_key(flag)
    hook_text = build_viral_hook(flag, county, short=False)
    if not hook_text:
        hook_text = (
            f"Why does {place}'s public checkbook show a pattern nobody's explaining "
            f"in plain language?"
        )
    hook_text = _sanitize_script(sanitize_hook(hook_text))

    hint = _build_hint(ctx, key)
    value = _build_value(flag, ctx, key)
    credibility = _build_credibility(place, source, key)
    takeaway = _build_takeaway(ctx, key)
    action = _build_action(place, key)

    copy = {
        "hook": hook_text,
        "hint": hint,
        "value": value,
        "credibility": credibility,
        "takeaway": takeaway,
        "action": action,
    }

    timing = (load_directive().get("hhvcta_timing") or {})
    beats_order = ["hook", "hint", "value", "credibility", "takeaway", "action"]
    script_body: list[dict[str, Any]] = []
    all_on_screen: list[str] = []

    for beat in beats_order:
        t = timing.get(beat) or {}
        start_s = t.get("start_s", 0)
        end_s = t.get("end_s", start_s + 3)
        duration_s = t.get("duration_s", end_s - start_s)
        bursts = _on_screen_bursts(key, ctx, beat)
        all_on_screen.extend(bursts)
        script_body.append(
            {
                "scene": beat.upper(),
                "hhvcta": beat,
                "start_s": start_s,
                "end_s": end_s,
                "duration_s": duration_s,
                "spoken_script": copy[beat],
                "on_screen_text": bursts,
                "visual_directives": _visual_directives(key, beat, flag),
            }
        )

    category = _flag_get(flag, "category", "flag")
    severity = _flag_get(flag, "severity", "high")
    evidence = _flag_get(flag, "evidence", "")
    description = _flag_get(flag, "description", "")

    return {
        "schema": "reclaw.viral_scribe.v1",
        "framework": "HHVCTA",
        "role": "Viral Scribe",
        "hook_text": hook_text,
        "script_body": script_body,
        "on_screen_text": list(dict.fromkeys(all_on_screen))[:12],
        "visual_directives": _visual_directives(key, "hook", flag) + _visual_directives(key, "value", flag),
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "jurisdiction": county,
            "place": place,
            "emotional_filter": key,
            "playbook_key": classify_flag(flag),
            "duration_s": 60,
            "review_id": review_id,
        },
        "anomaly": {
            "category": category,
            "severity": severity,
            "description": description,
            "data_point": ctx.get("amount_fmt") or ctx.get("amount_exact"),
            "vendor": ctx.get("vendor"),
            "provenance": source,
            "evidence": evidence,
        },
        "copy": copy,
        "disclaimer": DISCLAIMER,
        "playbook": get_playbook_visual(flag),
        "trigger_phrases": (load_playbook().get("trigger_phrases") or [])[:4],
    }


def build_scribe_from_json(report: dict[str, Any], *, county: str) -> dict[str, Any]:
    """Accept a JSON anomaly report (county-queue / API shape) and return scribe manifest."""
    flag = report
    if "red_flags" in report and report["red_flags"]:
        flag = report["red_flags"][0]
    source = report.get("source") or report.get("provenance") or "Indiana Gateway public records"
    return build_scribe_manifest(flag, county=county, source=source, review_id=report.get("review_id"))


def write_scribe_manifest(
    manifest: dict[str, Any],
    *,
    county: str,
    index: int = 1,
    out_dir: Path | None = None,
) -> Path:
    slug = county.lower().replace(" ", "_").replace("county", "").strip("_")
    target_dir = out_dir or (REPO_ROOT / "data" / "manifests" / slug)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-scribe-{index}.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path
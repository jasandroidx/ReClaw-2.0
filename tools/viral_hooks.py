"""
Story-first viral hooks from Project ReClaw HHVCTA playbook.

Never start with the data — start with the intent behind the data.
Fair-report guardrails: suspicious questions, not crime allegations.
"""

from __future__ import annotations

import json
import random
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from tools.public_data_loaders import REPO_ROOT

PLAYBOOK_PATH = REPO_ROOT / "data" / "viral_hook_playbook.yaml"
DEFAULT_THRESHOLD = 50_000

# Accusatory language blocked from hooks (playbook examples are sanitized).
_FORBIDDEN_RE = re.compile(
    r"\b("
    r"caught|sneaking|corrupt|criminal|guilty|stole|stealing|fraudster|"
    r"back door|embezzle|busted|scamming|scammer"
    r")\b",
    re.I,
)

_VENDOR_RE = re.compile(r"'([^']+)'")
_AMOUNT_RE = re.compile(r"\$([0-9][0-9,]*(?:\.\d{2})?)")
_TX_COUNT_RE = re.compile(r"(\d+)\s+disbursements?", re.I)
_DATE_RE = re.compile(r"on (\d{4}-\d{2}-\d{2})")
_WEEKEND_RE = re.compile(r"weekend payment", re.I)


def _short_dollars(x: float | None) -> str | None:
    if x is None:
        return None
    if x >= 1_000_000:
        return f"${x / 1_000_000:.1f} MILLION".replace(".0 ", " ")
    if x >= 1_000:
        return f"${x / 1_000:.0f}K"
    return f"${x:,.0f}"


def _parse_amount(text: str) -> float | None:
    m = _AMOUNT_RE.search(text or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _flag_get(flag: Any, key: str, default: Any = None) -> Any:
    if isinstance(flag, dict):
        return flag.get(key, default)
    return getattr(flag, key, default)


def _evidence_dict(flag: Any) -> dict[str, Any]:
    ev = _flag_get(flag, "evidence", "") or ""
    if not ev.strip().startswith("{"):
        return {}
    try:
        return json.loads(ev)
    except Exception:
        return {}


def _evidence_rule(flag: Any) -> str | None:
    ev = _evidence_dict(flag)
    rule = ev.get("rule")
    return str(rule) if rule else None


@lru_cache(maxsize=1)
def load_playbook() -> dict[str, Any]:
    if not PLAYBOOK_PATH.is_file():
        return {}
    return yaml.safe_load(PLAYBOOK_PATH.read_text(encoding="utf-8")) or {}


def _place_name(county: str) -> str:
    return county.replace(" County", "").strip()


def classify_flag(flag: Any) -> str | None:
    """Map a RedFlag to playbook red_flag_hooks key (smurfing, round_number, ...)."""
    pb = load_playbook()
    hooks = pb.get("red_flag_hooks") or {}
    cat = _flag_get(flag, "category", "") or ""
    rule = _evidence_rule(flag)
    desc = _flag_get(flag, "description", "") or ""

    for key, spec in hooks.items():
        cats = spec.get("categories") or []
        if cat not in cats:
            continue
        rules = spec.get("evidence_rules") or []
        if rules:
            if rule and rule in rules:
                return key
            if "weekend_payment" in rules and _WEEKEND_RE.search(desc):
                return key
            if "duplicate_vendor_amount_date" in rules and "duplicate payment" in desc.lower():
                return key
            if cat == "double_dip" and "double_dip" in cats:
                return key
            continue
        return key
    return None


def extract_hook_context(flag: Any, county: str) -> dict[str, Any]:
    """Pull template variables from flag description + evidence."""
    desc = _flag_get(flag, "description", "") or ""
    ev = _evidence_dict(flag)
    place = _place_name(county)

    vendor = ev.get("vendor")
    if not vendor:
        vm = _VENDOR_RE.search(desc)
        vendor = vm.group(1) if vm else None

    amount = ev.get("amount") or ev.get("total")
    if amount is not None:
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            amount = None
    if amount is None:
        amount = _parse_amount(desc)

    tx_count = ev.get("tx_count")
    if tx_count is None:
        tm = _TX_COUNT_RE.search(desc)
        tx_count = int(tm.group(1)) if tm else None

    date = ev.get("date")
    if not date:
        dm = _DATE_RE.search(desc)
        date = dm.group(1) if dm else None

    threshold = ev.get("threshold") or DEFAULT_THRESHOLD
    try:
        threshold = float(threshold)
    except (TypeError, ValueError):
        threshold = DEFAULT_THRESHOLD

    name, title = None, None
    if _flag_get(flag, "category", "") == "salary_shock":
        from tools.scriptwriter import _parse_salary_parts

        name, title = _parse_salary_parts(flag)

    day = "weekend"
    if date:
        try:
            from datetime import datetime

            dt = datetime.strptime(str(date)[:10], "%Y-%m-%d")
            day = dt.strftime("%A")
        except ValueError:
            day = "weekend"

    return {
        "place": place,
        "county": county,
        "vendor": vendor,
        "amount": amount,
        "amount_fmt": _short_dollars(amount),
        "amount_exact": f"${amount:,.2f}" if amount is not None else None,
        "tx_count": tx_count,
        "threshold": threshold,
        "threshold_fmt": f"${threshold:,.0f}",
        "date": date,
        "day": day,
        "name": name,
        "title": title,
        "category": _flag_get(flag, "category", ""),
    }


def _format_template(template: str, ctx: dict[str, Any]) -> str:
    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    try:
        return template.format_map(_SafeDict(ctx))
    except Exception:
        return template


def sanitize_hook(text: str) -> str:
    """Strip accusatory words; soften fraud-detection test phrasing for cold opens."""
    out = _FORBIDDEN_RE.sub("", text or "")
    out = re.sub(r"\s{2,}", " ", out).strip()
    out = out.replace("failed the fraud-detection test", "failed a forensic math test")
    out = out.replace("FAILED the Fraud-Detection Test", "failed a forensic math test")
    return out


def _pick_trigger_phrase(playbook_key: str | None) -> str | None:
    pb = load_playbook()
    phrases = pb.get("trigger_phrases") or []
    if not phrases:
        return None
    # Deterministic per playbook key for reproducible manifests
    if playbook_key:
        idx = sum(ord(c) for c in playbook_key) % len(phrases)
        return phrases[idx]
    return random.choice(phrases)


def _hook_from_templates(playbook_key: str, ctx: dict[str, Any], *, short: bool = False) -> str | None:
    pb = load_playbook()
    spec = (pb.get("red_flag_hooks") or {}).get(playbook_key) or {}
    templates = spec.get("hook_templates_short" if short else "hook_templates") or []
    if not templates:
        return None
    # Pick first template that has required fields filled
    required = spec.get("requires") or []
    for tpl in templates:
        if all(ctx.get(k) not in (None, "", "{" + k + "}") for k in required):
            return _format_template(tpl, ctx)
    return _format_template(templates[0], ctx) if templates else None


def build_viral_hook(flag: Any, county: str, *, short: bool = False) -> str | None:
    """
    Story-first hook for a single flag. Returns None if no playbook match.
    """
    key = classify_flag(flag)
    if not key:
        return None
    ctx = extract_hook_context(flag, county)
    hook = _hook_from_templates(key, ctx, short=short)
    if not hook:
        return None
    trigger = _pick_trigger_phrase(key)
    if trigger and not hook.lower().startswith(trigger.lower().rstrip(" —")):
        sep = "" if trigger.endswith(("—", "-", ":")) else " "
        hook = f"{trigger}{sep}{hook[0].lower()}{hook[1:]}" if len(hook) > 1 else f"{trigger}{sep}{hook}"
    return sanitize_hook(hook)


def get_playbook_visual(flag: Any) -> dict[str, str | None]:
    """Visual asset hints for Remotion HOOK scene."""
    key = classify_flag(flag)
    if not key:
        return {}
    spec = (load_playbook().get("red_flag_hooks") or {}).get(key) or {}
    return {
        "playbook_id": spec.get("playbook_id"),
        "visual_asset": spec.get("visual"),
        "vfx": spec.get("vfx"),
        "text_overlay": spec.get("text_overlay"),
    }


def headline_options(flag: Any, county: str, *, limit: int = 3) -> list[str]:
    """YouTube title variants from playbook headline_templates."""
    key = classify_flag(flag)
    if not key:
        return []
    spec = (load_playbook().get("red_flag_hooks") or {}).get(key) or {}
    ctx = extract_hook_context(flag, county)
    out: list[str] = []
    for tpl in (spec.get("headline_templates") or [])[:limit]:
        line = sanitize_hook(_format_template(tpl, ctx))
        if line and line not in out:
            out.append(line)
    return out
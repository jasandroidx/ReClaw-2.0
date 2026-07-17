"""
Auditor continuous-improvement playbook.

Loads living rule files so Silent Auditor + scriptwriter improve over time:
  - data/content_truth_rules.yaml
  - data/audit_pipeline_mistakes.yaml
  - data/public_source_map.yaml
  - data/indiana_public_finance_blueprint.yaml (optional)

Industry pattern (self-improving agents): persist lessons into shared context
files (AGENTS.md / playbooks), inject on every run — not chat memory.

Usage:
  from tools.auditor_playbook import load_playbook, filter_flags_by_truth, log_lesson
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from tools.public_data_loaders import REPO_ROOT

TRUTH_PATH = REPO_ROOT / "data" / "content_truth_rules.yaml"
MISTAKES_PATH = REPO_ROOT / "data" / "audit_pipeline_mistakes.yaml"
SOURCE_MAP_PATH = REPO_ROOT / "data" / "public_source_map.yaml"
BLUEPRINT_PATH = REPO_ROOT / "data" / "indiana_public_finance_blueprint.yaml"
STRATEGY_PATH = REPO_ROOT / "data" / "audit_strategy.yaml"
LESSONS_LOG = REPO_ROOT / "data" / "auditor_lessons_log.yaml"


def _safe_yaml_load(path: Path) -> dict[str, Any]:
    """Load YAML dict; never crash the audit pipeline on a bad rule file."""
    if not path.is_file():
        return {}
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except Exception as exc:  # noqa: BLE001 — durable rules must not break scans
        return {"_load_error": f"{path.name}: {exc}"}


@lru_cache(maxsize=1)
def load_playbook() -> dict[str, Any]:
    """Load all living auditor rule files (cached per process)."""
    out: dict[str, Any] = {
        "loaded_at": datetime.now(timezone.utc).isoformat(),
        "paths": {},
        "load_errors": [],
    }
    for key, path in (
        ("truth", TRUTH_PATH),
        ("mistakes", MISTAKES_PATH),
        ("source_map", SOURCE_MAP_PATH),
        ("blueprint", BLUEPRINT_PATH),
        ("strategy", STRATEGY_PATH),
    ):
        doc = _safe_yaml_load(path)
        if doc.get("_load_error"):
            out["load_errors"].append(doc["_load_error"])
            out[key] = {}
        else:
            out[key] = doc
            if path.is_file():
                try:
                    out["paths"][key] = str(path.relative_to(REPO_ROOT))
                except ValueError:
                    out["paths"][key] = str(path)
    return out


def reload_playbook() -> dict[str, Any]:
    load_playbook.cache_clear()
    return load_playbook()


def forbidden_vendor_names() -> set[str]:
    pb = load_playbook()
    truth = pb.get("truth") or {}
    names = set()
    for n in truth.get("forbidden_as_vendor_or_company") or []:
        names.add(str(n).strip().lower())
    # blueprint hard_kill if present
    bp = pb.get("blueprint") or {}
    hk = bp.get("hard_kill") or {}
    for n in hk.get("rollup_entities") or []:
        names.add(str(n).strip().lower())
    for n in hk.get("category_only_disburse_names") or []:
        names.add(str(n).strip().lower())
    for n in hk.get("payroll_aggregate_lines") or []:
        names.add(str(n).strip().lower())
    return {n for n in names if n}


def forbidden_hook_phrases() -> list[str]:
    truth = (load_playbook().get("truth") or {})
    return list(truth.get("forbidden_language_in_hooks") or [])


def open_content_rules() -> list[str]:
    """Human-readable rules for SOUL / review cards."""
    lines = [
        "Living playbook active: content_truth_rules + mistakes + source_map.",
        "Never treat Gateway ent_name/disburse_name as a private company payee.",
        "Prefer SBOA final findings + Form 100R + dual-receipt stories over IsolationForest volume.",
        "Every publishable short: named actor + exact $ + contrast + receipt.",
        "Fair-report only: no embezzled/stole/corrupt/fraud/theft allegations.",
        "After human reject or new research: log_lesson() so the next run improves.",
    ]
    mistakes = (load_playbook().get("mistakes") or {}).get("mistakes") or []
    open_ids = [m.get("id") for m in mistakes if m.get("status") in ("open", "in_progress", "partial")]
    if open_ids:
        lines.append("Open mistakes to respect: " + ", ".join(str(i) for i in open_ids[:12]))
    return lines


def _flag_text(flag: Any) -> str:
    if isinstance(flag, dict):
        return f"{flag.get('category','')} {flag.get('description','')} {flag.get('evidence','')}"
    cat = getattr(flag, "category", "") or ""
    desc = getattr(flag, "description", "") or ""
    ev = getattr(flag, "evidence", "") or ""
    return f"{cat} {desc} {ev}"


def filter_flags_by_truth(flags: list[Any]) -> tuple[list[Any], list[str]]:
    """
    Drop flags that violate living content_truth / hard kill lists.
    Returns (kept, drop_reasons).
    """
    forbidden = forbidden_vendor_names()
    phrases = [p.lower() for p in forbidden_hook_phrases() if p]
    kept: list[Any] = []
    reasons: list[str] = []

    vendorish = {
        "split_purchase",
        "split_purchase_pattern",
        "vendor_concentration",
        "round_number_cluster",
    }

    for f in flags:
        cat = (f.get("category") if isinstance(f, dict) else getattr(f, "category", "")) or ""
        text = _flag_text(f)
        low = text.lower()

        # Kill explicit forbidden phrases in descriptions
        bad_phrase = next((p for p in phrases if p in low), None)
        if bad_phrase:
            reasons.append(f"drop {cat}: forbidden phrase '{bad_phrase}'")
            continue

        # Vendor-style categories: kill if any forbidden token appears as entity
        if cat in vendorish:
            # quoted entity or leading 'X' pattern
            m = re.search(r"'([^']+)'", text)
            entity = (m.group(1) if m else "").strip().lower()
            if entity in forbidden or any(
                re.search(rf"\b{re.escape(n)}\b", low) for n in forbidden if len(n) > 2
            ):
                reasons.append(f"drop {cat}: forbidden vendor/rollup '{entity or 'matched'}'")
                continue
            # No real entity at all → drop vendor claims
            if not entity and "governmental activities" in low:
                reasons.append(f"drop {cat}: governmental activities")
                continue

        kept.append(f)

    return kept, reasons


def playbook_context_for_session() -> str:
    """Short text block to inject into session logs / review provenance."""
    rules = open_content_rules()
    pb = load_playbook()
    paths = pb.get("paths") or {}
    return (
        "AUDITOR PLAYBOOK LOADED\n"
        + "\n".join(f"- {r}" for r in rules)
        + "\nFiles: "
        + ", ".join(f"{k}={v}" for k, v in paths.items())
    )


def log_lesson(
    *,
    lesson_id: str,
    symptom: str,
    root_cause: str,
    content_rule: str,
    status: str = "open",
    county_example: str | list[str] | None = None,
    fix: str = "pending — update code/rules on next pass",
    also_update_truth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Append a lesson so future agents improve.

    1) Appends to data/audit_pipeline_mistakes.yaml (if id new)
    2) Appends to data/auditor_lessons_log.yaml (always, timestamped)
    3) Optionally merges keys into content_truth_rules.yaml
    """
    lesson_id = re.sub(r"[^a-z0-9_\-]+", "-", lesson_id.lower()).strip("-")
    entry = {
        "id": lesson_id,
        "symptom": symptom,
        "root_cause": root_cause,
        "content_rule": content_rule,
        "status": status,
        "fix": fix,
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }
    if county_example is not None:
        entry["county_example"] = county_example

    # Mistakes YAML
    mistakes_doc: dict[str, Any] = {}
    if MISTAKES_PATH.is_file():
        mistakes_doc = yaml.safe_load(MISTAKES_PATH.read_text(encoding="utf-8")) or {}
    mistakes_list = list(mistakes_doc.get("mistakes") or [])
    existing_ids = {m.get("id") for m in mistakes_list}
    if lesson_id not in existing_ids:
        mistakes_list.append(
            {
                "id": lesson_id,
                "county_example": county_example,
                "symptom": symptom,
                "root_cause": root_cause,
                "fix": fix,
                "status": status,
                "content_rule": content_rule,
            }
        )
        mistakes_doc["mistakes"] = mistakes_list
        MISTAKES_PATH.write_text(
            yaml.safe_dump(mistakes_doc, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    # Chronological log
    log_doc: dict[str, Any] = {"lessons": []}
    if LESSONS_LOG.is_file():
        log_doc = yaml.safe_load(LESSONS_LOG.read_text(encoding="utf-8")) or {"lessons": []}
    lessons = list(log_doc.get("lessons") or [])
    lessons.append(entry)
    log_doc["lessons"] = lessons[-200:]  # cap
    LESSONS_LOG.write_text(
        yaml.safe_dump(log_doc, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    # Optional truth merge
    if also_update_truth and TRUTH_PATH.is_file():
        truth = yaml.safe_load(TRUTH_PATH.read_text(encoding="utf-8")) or {}
        for k, v in also_update_truth.items():
            if isinstance(v, list) and isinstance(truth.get(k), list):
                # merge unique strings
                cur = [str(x) for x in truth[k]]
                for item in v:
                    if str(item) not in cur:
                        cur.append(str(item))
                truth[k] = cur
            else:
                truth[k] = v
        TRUTH_PATH.write_text(
            yaml.safe_dump(truth, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    reload_playbook()
    return {"ok": True, "lesson_id": lesson_id, "mistakes_path": str(MISTAKES_PATH), "log": str(LESSONS_LOG)}


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Auditor playbook load / log lesson")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--log-id", default="")
    ap.add_argument("--symptom", default="")
    ap.add_argument("--root-cause", default="")
    ap.add_argument("--rule", default="")
    args = ap.parse_args()
    if args.show:
        print(playbook_context_for_session())
        print(json.dumps({"forbidden_vendors_sample": sorted(forbidden_vendor_names())[:20]}, indent=2))
    elif args.log_id:
        print(
            json.dumps(
                log_lesson(
                    lesson_id=args.log_id,
                    symptom=args.symptom or "unspecified",
                    root_cause=args.root_cause or "unspecified",
                    content_rule=args.rule or "unspecified",
                ),
                indent=2,
            )
        )
    else:
        ap.print_help()

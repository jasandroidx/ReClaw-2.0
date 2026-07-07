"""
Remotion-ready video manifest generator — HHVCTA framework (60s vertical).

v1: timeline beats (start_s/end_s)
v2: scene array with visual_asset / vfx / audio_pipeline for Remotion React comps

Does not render video. Fair-report language only — patterns in public records.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.public_data_loaders import REPO_ROOT
from tools.viral_hooks import build_viral_hook, get_playbook_visual, load_playbook, sanitize_hook
from tools.viral_scribe import build_scribe_manifest

MANIFEST_DIR = REPO_ROOT / "data" / "manifests"
DISCLAIMER = (
    "Patterns in public financial records only. Not an allegation of crime or wrongdoing."
)

# ElevenLabs voice — override via ELEVENLABS_VOICE_ID env at render time
DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"


def _normalize_anomaly(category: str, anomaly_label: str | None = None) -> str:
    raw = (anomaly_label or category or "").lower().replace("_", " ")
    if "benford" in raw:
        return "benfords_law"
    if "split" in raw or "smurf" in raw or "threshold" in raw:
        return "split_purchases"
    if "round" in raw:
        return "round_number"
    if "duplicate" in raw or "double" in raw:
        return "duplicate_payment"
    if "weekend" in raw or "holiday" in raw:
        return "weekend_drop"
    if "salary" in raw:
        return "salary_shock"
    return "generic"


def _script_copy(
    jurisdiction: str,
    anomaly_key: str,
    data_point: str,
    source_name: str,
    *,
    hook_line: str | None = None,
    finding: str | None = None,
) -> dict[str, str]:
    """HHVCTA spoken scripts — viral retention, fair-report framing."""
    place = jurisdiction.replace(" County", "").strip()

    if hook_line:
        hook = sanitize_hook(hook_line)
    elif anomaly_key == "benfords_law":
        hook = (
            f"{place}'s public checkbook just failed a forensic math test. "
            f"I ran Benford's Law on the official data."
        )
    elif anomaly_key == "split_purchases":
        hook = (
            f"Why did {place} send dozens of payments to the same vendor in one fiscal year — "
            f"each just under the bidding threshold?"
        )
    elif anomaly_key == "round_number":
        hook = (
            f"They thought you wouldn't check the cents. Why did one vendor get exactly "
            f"{data_point} with zero change on {place}'s public ledger?"
        )
    elif anomaly_key == "weekend_drop":
        hook = (
            f"What was {place} buying on a weekend? The county's own public records show "
            f"a {data_point} payout on the calendar."
        )
    elif anomaly_key == "duplicate_payment":
        hook = (
            f"Either the accounting system glitched — or the same vendor got paid twice. "
            f"I ran the math on {place}'s public checkbook."
        )
    elif anomaly_key == "salary_shock":
        hook = (
            f"{place} County taxpayers paid {data_point} on one public paycheck. "
            f"The record is official."
        )
    else:
        hook = f"We found an unusual pattern in {place}'s public ledgers that nobody's explaining."

    if finding:
        value = finding
    elif anomaly_key == "benfords_law":
        value = (
            f"I ran the disbursement amounts through Benford's Law — a test auditors use on "
            f"invoice data. The distribution flagged around {data_point}. That doesn't prove "
            f"fraud, but it's a reason to pull receipts."
        )
    elif anomaly_key == "split_purchases":
        value = (
            f"Multiple sub-threshold payments clustering near {data_point} can match "
            f"split-purchase patterns under Indiana bidding rules. The numbers are public — "
            f"the explanation should be too."
        )
    elif anomaly_key == "salary_shock":
        value = (
            f"Public compensation records show {data_point}. In a small county, that's a "
            f"legitimate taxpayer question — not an accusation."
        )
    else:
        value = (
            f"The data shows a standout line item: {data_point}. It came from {source_name}. "
            f"Anomalies can have innocent explanations — but silence isn't one of them."
        )

    hint = "Forensic accountants use these tests on public ledgers. So can taxpayers."
    credibility = (
        f"This isn't rumor. It's from {source_name} — pulled from official open records."
    )
    takeaway = "It's your tax money. Fair questions deserve answers on the record."
    action = (
        f"If you live in {place}, tag your local officials and ask them to explain this line "
        f"at the next public meeting."
    )

    return {
        "hook": hook,
        "hint": hint,
        "value": value,
        "credibility": credibility,
        "takeaway": takeaway,
        "action": action,
    }


def _hook_scene_visuals(category: str, *, playbook: dict[str, str | None] | None = None) -> dict[str, str | None]:
    pb = playbook or {}
    if pb.get("visual_asset") or pb.get("text_overlay"):
        return {
            "text_overlay": pb.get("text_overlay") or "PUBLIC RECORD",
            "visual_asset": pb.get("visual_asset") or "courthouse_stock_darkened",
            "vfx": pb.get("vfx") or "subtle_camera_push",
            "playbook_id": pb.get("playbook_id"),
        }
    key = _normalize_anomaly(category)
    defaults = {
        "split_purchases": ("JUST UNDER THE LIMIT?", "receipt_flash_under_threshold", "rapid_receipt_flash"),
        "round_number": ("ZERO CENTS?", "compare_real_vs_round_invoice", "highlight_zero_cents"),
        "weekend_drop": ("WEEKEND PAYOUT?", "timestamp_sunday_2am", "clock_overlay"),
        "duplicate_payment": ("PAID TWICE?", "duplicate_check_side_by_side", "search_animation"),
        "salary_shock": ("YOUR TAX DOLLARS", "salary_table_highlight", "subtle_camera_push"),
        "benfords_law": ("THE MATH", "benford_digit_chart", "glitch_transition"),
    }
    if key in defaults:
        overlay, visual, vfx = defaults[key]
        return {"text_overlay": overlay, "visual_asset": visual, "vfx": vfx}
    return {"text_overlay": "PUBLIC RECORD", "visual_asset": "courthouse_stock_darkened", "vfx": "subtle_camera_push"}


def _remotion_scenes(
    copy: dict[str, str],
    *,
    data_point: str,
    source_name: str,
    jurisdiction: str,
    category: str = "atomic_finding",
    playbook: dict[str, str | None] | None = None,
) -> list[dict]:
    """Scene timeline for Remotion composition (~29.5s core + padding to 60s in renderer)."""
    place = jurisdiction.replace(" County", "").strip()
    hook_vis = _hook_scene_visuals(category, playbook=playbook)
    return [
        {
            "scene_id": 1,
            "type": "HOOK",
            "hhvcta": "hook",
            "duration_seconds": 3.0,
            "text_overlay": hook_vis["text_overlay"],
            "spoken_script": copy["hook"],
            "visual_asset": hook_vis["visual_asset"],
            "vfx": hook_vis["vfx"],
            **({"playbook_id": hook_vis["playbook_id"]} if hook_vis.get("playbook_id") else {}),
        },
        {
            "scene_id": 2,
            "type": "HINT",
            "hhvcta": "hint",
            "duration_seconds": 2.5,
            "text_overlay": "The Math Is Public",
            "spoken_script": copy["hint"],
            "visual_asset": "benford_chart_skeleton",
            "vfx": "glitch_transition",
        },
        {
            "scene_id": 3,
            "type": "VALUE",
            "hhvcta": "value",
            "duration_seconds": 12.0,
            "text_overlay": f"Flag: {data_point[:40]}",
            "spoken_script": copy["value"],
            "visual_asset": "dynamic_chart_render",
            "chart": {"type": "bar_highlight", "highlight": data_point},
            "vfx": "zoom_in_on_chart",
        },
        {
            "scene_id": 4,
            "type": "CREDIBILITY",
            "hhvcta": "credibility",
            "duration_seconds": 4.0,
            "text_overlay": f"Source: {source_name[:36]}",
            "spoken_script": copy["credibility"],
            "visual_asset": "screenshot_open_data_portal",
            "vfx": "highlight_source_url",
        },
        {
            "scene_id": 5,
            "type": "TAKEAWAY",
            "hhvcta": "takeaway",
            "duration_seconds": 4.0,
            "text_overlay": "Your Tax Dollars",
            "spoken_script": copy["takeaway"],
            "visual_asset": "data_table_scroll",
            "vfx": None,
        },
        {
            "scene_id": 6,
            "type": "ACTION",
            "hhvcta": "action",
            "duration_seconds": 4.0,
            "text_overlay": f"Tag {place}",
            "spoken_script": copy["action"],
            "visual_asset": "cta_subscribe_card",
            "vfx": "red_border_pulse",
        },
    ]


def _hhvcta_beats(copy: dict[str, str], *, hook_on_screen: str) -> dict[str, Any]:
    """Timeline beats derived from scene copy (v1 compat)."""
    return {
        "hook": {"start_s": 0, "end_s": 3, "text": copy["hook"], "on_screen": hook_on_screen[:80]},
        "hint": {"start_s": 3, "end_s": 5.5, "text": copy["hint"]},
        "value": {"start_s": 5.5, "end_s": 17.5, "text": copy["value"]},
        "credibility": {"start_s": 17.5, "end_s": 21.5, "text": copy["credibility"], "on_screen": copy["credibility"][:80]},
        "takeaway": {"start_s": 21.5, "end_s": 25.5, "text": copy["takeaway"]},
        "action": {"start_s": 25.5, "end_s": 29.5, "text": copy["action"], "cta": "subscribe"},
    }


def generate_viral_manifest(
    jurisdiction: str,
    anomaly_type: str,
    data_point: str,
    source_name: str,
    *,
    hook_line: str | None = None,
    finding: str | None = None,
    category: str = "atomic_finding",
    severity: str = "high",
    review_id: str | None = None,
    playbook: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    """
    Remotion-compatible JSON manifest (HHVCTA).

    jurisdiction: city or county name (e.g. 'Gibson' or 'Chicago')
    anomaly_type: human label or RedFlag category
    """
    anomaly_key = _normalize_anomaly(category, anomaly_type)
    copy = _script_copy(
        jurisdiction,
        anomaly_key,
        data_point,
        source_name,
        hook_line=hook_line,
        finding=finding,
    )
    scenes = _remotion_scenes(
        copy,
        data_point=data_point,
        source_name=source_name,
        jurisdiction=jurisdiction,
        category=category,
        playbook=playbook,
    )
    beats = _hhvcta_beats(copy, hook_on_screen=hook_line or copy["hook"])
    word_count = sum(len(copy[k].split()) for k in copy)
    pb_meta = playbook or {}
    trigger_phrases = (load_playbook().get("trigger_phrases") or [])[:4]

    return {
        "schema": "reclaw.video_manifest.v2",
        "framework": "HHVCTA",
        "metadata": {
            "project": "Project Reclaw",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "target": jurisdiction.replace(" County", "").strip(),
            "anomaly": anomaly_type,
            "anomaly_key": anomaly_key,
            "render_resolution": [1080, 1920],
            "fps": 30,
            "duration_s": 60,
            "review_id": review_id,
        },
        "audio_pipeline": {
            "tts_provider": "elevenlabs",
            "voice_id": DEFAULT_VOICE_ID,
            "bgm": "suspense_drone_01.mp3",
            "captions": "whisper.cpp → @remotion/captions",
        },
        "atomic_finding": {
            "category": category,
            "severity": severity,
            "data_point": data_point,
            "provenance": source_name,
            "description": finding or copy["value"],
        },
        "scenes": scenes,
        "beats": beats,
        "word_count": word_count,
        "disclaimer": DISCLAIMER,
        "playbook": {
            "id": pb_meta.get("playbook_id"),
            "trigger_phrases": trigger_phrases,
            "psychology_rule": (load_playbook().get("psychology") or {}).get("rule"),
        },
    }


def build_short_manifest(
    *,
    county: str,
    hook: str,
    finding: str,
    evidence: str,
    category: str,
    severity: str,
    amount: str | None = None,
    population: int | None = None,
    review_id: str | None = None,
    playbook: dict[str, str | None] | None = None,
    flag: Any | None = None,
) -> dict[str, Any]:
    """Build v2 manifest from county-queue / scriptwriter fields."""
    data_point = amount or _first_dollar(finding) or _snippet(finding, 60)
    source = _clean_source(evidence)
    label = category.replace("_", " ").title()
    hook_line = hook
    scribe_manifest: dict[str, Any] | None = None
    if flag is not None:
        scribe_manifest = build_scribe_manifest(flag, county=county, source=source, review_id=review_id)
        hook_line = scribe_manifest.get("hook_text") or hook_line
        generated = build_viral_hook(flag, county, short=True)
        if generated and not scribe_manifest.get("hook_text"):
            hook_line = generated
        playbook = playbook or get_playbook_visual(flag)
    manifest = generate_viral_manifest(
        county,
        label,
        data_point,
        source,
        hook_line=hook_line,
        finding=finding,
        category=category,
        severity=severity,
        review_id=review_id,
        playbook=playbook,
    )
    if population:
        manifest["atomic_finding"]["population"] = population
    if scribe_manifest:
        manifest["scribe"] = scribe_manifest
        manifest["hook_text"] = scribe_manifest["hook_text"]
        manifest["script_body"] = scribe_manifest["script_body"]
        manifest["on_screen_text"] = scribe_manifest["on_screen_text"]
        manifest["visual_directives"] = scribe_manifest["visual_directives"]
        # Align Remotion scene copy + timing with Viral Scribe HHVCTA (60s)
        copy = scribe_manifest["copy"]
        manifest["beats"] = {
            beat["hhvcta"]: {
                "start_s": beat["start_s"],
                "end_s": beat["end_s"],
                "text": beat["spoken_script"],
                "on_screen": " · ".join(beat["on_screen_text"]),
            }
            for beat in scribe_manifest["script_body"]
        }
        for scene in manifest.get("scenes", []):
            hhvcta = scene.get("hhvcta")
            if hhvcta and hhvcta in copy:
                scene["spoken_script"] = copy[hhvcta]
            for sb in scribe_manifest["script_body"]:
                if sb["hhvcta"] == hhvcta:
                    scene["duration_seconds"] = sb["duration_s"]
                    scene["on_screen_text"] = sb["on_screen_text"]
                    scene["visual_directives"] = sb["visual_directives"]
                    break
    return manifest


def _first_dollar(text: str) -> str | None:
    m = re.search(r"\$[\d,]+(?:\.\d{2})?", text or "")
    return m.group(0) if m else None


def _snippet(text: str, n: int) -> str:
    t = (text or "").strip()
    return t[:n] + ("…" if len(t) > n else "")


def _clean_source(evidence: str) -> str:
    if evidence.strip().startswith("{"):
        try:
            ev = json.loads(evidence)
            return ev.get("source", "Indiana Gateway") or "Indiana Gateway public records"
        except Exception:
            pass
    if "gateway" in evidence.lower():
        return "Indiana Gateway"
    if len(evidence) > 120:
        return evidence[:120]
    return evidence or "Indiana Gateway public records"


def _flag_for_short(short: Any, red_flags: list[Any]) -> Any | None:
    cat = getattr(short, "source_flag_category", None) or (
        short.get("category") if isinstance(short, dict) else None
    )
    if cat and red_flags:
        for f in red_flags:
            fc = getattr(f, "category", None) or (f.get("category") if isinstance(f, dict) else None)
            if fc == cat:
                return f
    return red_flags[0] if red_flags else None


def write_manifests_for_package(
    county: str,
    shorts: list[Any],
    *,
    review_id: str | None = None,
    top_finding: str = "",
    top_evidence: str = "",
    red_flags: list[Any] | None = None,
) -> list[Path]:
    """Write v2 JSON manifests for each short in data/manifests/{county}/."""
    slug = county.lower().replace(" ", "_").replace("county", "").strip("_")
    out_dir = MANIFEST_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for i, s in enumerate(shorts[:5]):
        hook = getattr(s, "hook", None) or (s.get("hook") if isinstance(s, dict) else "")
        cat = getattr(s, "source_flag_category", None) or (
            s.get("category") if isinstance(s, dict) else "flag"
        )
        prov = getattr(s, "provenance", None) or (
            s.get("provenance") if isinstance(s, dict) else top_evidence
        )
        pb = s.get("playbook") if isinstance(s, dict) else None
        finding = top_finding if i == 0 else hook
        flag = _flag_for_short(s, red_flags or [])
        manifest = build_short_manifest(
            county=county,
            hook=hook or f"{county} — public money question",
            finding=finding,
            evidence=prov or top_evidence or "Indiana Gateway public records",
            category=cat or "atomic_finding",
            severity="high",
            review_id=review_id,
            playbook=pb,
            flag=flag,
        )
        path = out_dir / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-short-{i+1}.json"
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        paths.append(path)
    return paths


def write_manifest_file(manifest: dict[str, Any], path: Path | None = None) -> Path:
    target = path or MANIFEST_DIR / f"manifest_{manifest['metadata']['target'].replace(' ', '_').lower()}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return target
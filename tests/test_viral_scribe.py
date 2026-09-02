"""Viral Scribe HHVCTA manifest generator."""

import json

from core.handoff import RedFlag
from tools.viral_scribe import build_scribe_manifest, load_directive


def _split_flag() -> RedFlag:
    return RedFlag(
        severity="high",
        category="split_purchase",
        description=(
            "Gibson County FY2024: 'ACME Consulting LLC' received 8 disbursements "
            "each under $50,000, totaling $312,000"
        ),
        evidence=json.dumps(
            {"vendor": "ACME Consulting LLC", "tx_count": 8, "total": 312_000, "source": "gateway"}
        ),
    )


def test_directive_loads_hhvcta_timing():
    d = load_directive()
    assert d["hhvcta_timing"]["hook"]["end_s"] == 3
    assert d["hhvcta_timing"]["value"]["duration_s"] == 39


def test_manifest_has_required_fields():
    m = build_scribe_manifest(_split_flag(), county="Gibson County")
    assert m["schema"] == "reclaw.viral_scribe.v1"
    assert m["hook_text"]
    assert len(m["script_body"]) == 6
    assert m["on_screen_text"]
    assert m["visual_directives"]
    assert "ACME" in m["hook_text"]


def test_hhvcta_scene_order_and_timing():
    m = build_scribe_manifest(_split_flag(), county="Gibson County")
    scenes = m["script_body"]
    assert scenes[0]["hhvcta"] == "hook"
    assert scenes[0]["start_s"] == 0
    assert scenes[-1]["hhvcta"] == "action"
    assert scenes[-1]["end_s"] == 60


def test_fair_report_no_accusatory_verbs():
    m = build_scribe_manifest(_split_flag(), county="Gibson County")
    blob = json.dumps(m).lower()
    for bad in ("caught", "faking", "embezzle", "corrupt"):
        assert bad not in blob


def test_value_beat_has_eli5():
    m = build_scribe_manifest(_split_flag(), county="Gibson County")
    value = m["copy"]["value"].lower()
    assert "indiana" in value or "vote" in value or "threshold" in value or "limit" in value


def test_on_screen_bursts_short():
    m = build_scribe_manifest(_split_flag(), county="Gibson County")
    for scene in m["script_body"]:
        assert len(scene["on_screen_text"]) <= 3
        for burst in scene["on_screen_text"]:
            assert len(burst.split()) <= 3
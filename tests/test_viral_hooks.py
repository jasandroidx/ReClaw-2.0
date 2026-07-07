"""Viral hook playbook — story-first, fair-report hooks."""

import json

from core.handoff import RedFlag
from tools.viral_hooks import (
    build_viral_hook,
    classify_flag,
    get_playbook_visual,
    headline_options,
    load_playbook,
    sanitize_hook,
)
from tools.scriptwriter import _pick_hook, build_shorts
from tools.audit_adapter import AuditResult
from tools.video_manifest import generate_viral_manifest


def _split_flag() -> RedFlag:
    return RedFlag(
        severity="high",
        category="split_purchase",
        description=(
            "Gibson County FY2024: 'ACME Consulting LLC' received 8 disbursements "
            "each under $50,000, totaling $312,000 — possible bid-threshold splitting."
        ),
        evidence=json.dumps(
            {"vendor": "ACME Consulting LLC", "tx_count": 8, "total": 312_000, "source": "gateway"}
        ),
    )


def _round_flag() -> RedFlag:
    return RedFlag(
        severity="medium",
        category="round_number_cluster",
        description="Gibson County: round-dollar payment $50,000 to 'Mystery LLC'",
        evidence=json.dumps(
            {"vendor": "Mystery LLC", "amount": 50_000, "rule": "round_dollar", "source": "inbox"}
        ),
    )


def _salary_flag() -> RedFlag:
    return RedFlag(
        severity="high",
        category="salary_shock",
        description=(
            "Vanoven, Bruce L — Sheriff (County): $111,307 in 2025 public compensation. "
            "In a county of ~33,006, that's a taxpayer talking-point."
        ),
        evidence="gateway.ifionline.org Employee Compensation export",
    )


def test_playbook_loads():
    pb = load_playbook()
    assert pb.get("psychology", {}).get("rule")
    assert len(pb.get("trigger_phrases", [])) >= 3


def test_classify_split_purchase():
    assert classify_flag(_split_flag()) == "smurfing"


def test_story_first_hook_not_data_first():
    hook = build_viral_hook(_split_flag(), "Gibson County")
    assert hook
    assert "ACME Consulting" in hook
    low = hook.lower()
    assert "why did" in low or "math" in low or "thought you" in low
    assert "caught" not in hook.lower()
    assert "corrupt" not in hook.lower()


def test_salary_hook_uses_trigger_phrase():
    hook = build_viral_hook(_salary_flag(), "Gibson County", short=True)
    assert hook
    assert "Vanoven" in hook
    assert "Sheriff" in hook


def test_round_number_hook():
    hook = build_viral_hook(_round_flag(), "Gibson County", short=True)
    assert hook
    assert "Mystery LLC" in hook
    assert "cents" in hook.lower() or "pennies" in hook.lower() or ".00" in hook


def test_sanitize_strips_accusatory_words():
    raw = "Did this councilman get caught sneaking money out the back door?"
    clean = sanitize_hook(raw)
    assert "caught" not in clean.lower()
    assert "sneaking" not in clean.lower()


def test_scriptwriter_uses_viral_hook():
    hook = _pick_hook([_split_flag()], "Gibson County")
    assert "ACME" in hook or "8" in hook
    salary_hook = _pick_hook([_salary_flag()], "Gibson County")
    assert "Vanoven" in salary_hook


def test_shorts_include_playbook_visuals():
    result = AuditResult(county="Gibson County", red_flags=[_round_flag()])
    shorts, _ = build_shorts(result, county="Gibson County")
    assert shorts[0].get("playbook", {}).get("text_overlay") == "ZERO CENTS?"


def test_manifest_hook_scene_uses_playbook_overlay():
    m = generate_viral_manifest(
        "Gibson",
        "split_purchase",
        "$49,999",
        "Indiana Gateway",
        category="split_purchase",
        playbook=get_playbook_visual(_split_flag()),
    )
    assert m["scenes"][0]["text_overlay"] == "JUST UNDER THE LIMIT?"
    assert m["playbook"]["trigger_phrases"]


def test_headline_options():
    titles = headline_options(_salary_flag(), "Gibson County")
    assert any("Sheriff" in t for t in titles)
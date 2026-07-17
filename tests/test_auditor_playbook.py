"""Continuous-improvement playbook: load, filter, log_lesson."""

from __future__ import annotations

from pathlib import Path

import yaml

from core.handoff import RedFlag
from tools import auditor_playbook as ap


def test_mistakes_yaml_is_valid():
    doc = yaml.safe_load(ap.MISTAKES_PATH.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    assert isinstance(doc.get("mistakes"), list)
    assert len(doc["mistakes"]) >= 5


def test_load_playbook_has_truth_and_mistakes():
    ap.reload_playbook()
    pb = ap.load_playbook()
    assert pb.get("load_errors") == [] or "mistakes" in pb.get("paths", {})
    assert (pb.get("truth") or {}).get("forbidden_as_vendor_or_company")
    mistakes = (pb.get("mistakes") or {}).get("mistakes") or []
    assert any(m.get("id") == "gateway-ent-name-not-vendor" for m in mistakes)


def test_filter_drops_gateway_rollup_vendors():
    flags = [
        RedFlag(
            severity="high",
            category="split_purchase",
            description="69 checks to 'WATER' under $150k threshold",
            evidence="gateway ent_name",
        ),
        RedFlag(
            severity="high",
            category="vendor_concentration",
            description="Governmental Activities dominates disbursements",
            evidence="rollup",
        ),
        RedFlag(
            severity="critical",
            category="sboa_finding",
            description="SBOA special investigation: Clark missing $482,000",
            evidence="report 84477I p.3",
        ),
        {
            "category": "split_purchase",
            "description": "pattern on 'None' vendor",
            "evidence": "x",
        },
    ]
    kept, reasons = ap.filter_flags_by_truth(flags)
    assert len(reasons) >= 2
    kept_text = " ".join(
        (f.description if isinstance(f, RedFlag) else f.get("description", ""))
        for f in kept
    )
    assert "SBOA special investigation" in kept_text
    assert "WATER" not in kept_text or "sboa" in kept_text.lower()
    # rollup vendor flags should be gone
    cats = [
        (f.category if isinstance(f, RedFlag) else f.get("category")) for f in kept
    ]
    assert "split_purchase" not in cats or all(
        "WATER" not in (
            f.description if isinstance(f, RedFlag) else str(f.get("description", ""))
        )
        for f in kept
        if (f.category if isinstance(f, RedFlag) else f.get("category")) == "split_purchase"
    )


def test_filter_drops_forbidden_hook_phrases():
    flags = [
        {
            "category": "budget_anomaly",
            "description": "line flagged by IsolationForest in department X",
            "evidence": "dogegpt",
        }
    ]
    kept, reasons = ap.filter_flags_by_truth(flags)
    assert kept == []
    assert any("forbidden phrase" in r for r in reasons)


def test_log_lesson_appends(tmp_path, monkeypatch):
    mistakes = tmp_path / "mistakes.yaml"
    lessons = tmp_path / "lessons.yaml"
    truth = tmp_path / "truth.yaml"
    mistakes.write_text("mistakes: []\n", encoding="utf-8")
    truth.write_text("forbidden_as_vendor_or_company: []\n", encoding="utf-8")

    monkeypatch.setattr(ap, "MISTAKES_PATH", mistakes)
    monkeypatch.setattr(ap, "LESSONS_LOG", lessons)
    monkeypatch.setattr(ap, "TRUTH_PATH", truth)
    ap.reload_playbook()

    out = ap.log_lesson(
        lesson_id="unit-test-lesson",
        symptom="dry hooks",
        root_cause="no dual receipt",
        content_rule="require SBOA or rate story",
        county_example="Gibson",
        also_update_truth={"forbidden_as_vendor_or_company": ["TEST_ROLLUP_VENDOR"]},
    )
    assert out["ok"] is True
    mdoc = yaml.safe_load(mistakes.read_text(encoding="utf-8"))
    assert any(m.get("id") == "unit-test-lesson" for m in mdoc["mistakes"])
    ldoc = yaml.safe_load(lessons.read_text(encoding="utf-8"))
    assert any(x.get("id") == "unit-test-lesson" for x in ldoc["lessons"])
    tdoc = yaml.safe_load(truth.read_text(encoding="utf-8"))
    assert "TEST_ROLLUP_VENDOR" in tdoc["forbidden_as_vendor_or_company"]

    # second call with same id does not duplicate mistakes list
    ap.log_lesson(
        lesson_id="unit-test-lesson",
        symptom="again",
        root_cause="again",
        content_rule="again",
    )
    mdoc2 = yaml.safe_load(mistakes.read_text(encoding="utf-8"))
    assert sum(1 for m in mdoc2["mistakes"] if m.get("id") == "unit-test-lesson") == 1


def test_playbook_context_mentions_open_mistakes():
    ap.reload_playbook()
    ctx = ap.playbook_context_for_session()
    assert "AUDITOR PLAYBOOK LOADED" in ctx
    assert "Living playbook" in ctx

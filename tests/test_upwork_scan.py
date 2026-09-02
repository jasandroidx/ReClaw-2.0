"""Upwork scorer + demo digest path."""

from tools.upwork_scan import JobHit, fetch_demo, load_prefs, score_job
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_prefs_load():
    prefs = load_prefs(ROOT / "data" / "upwork_preferences.yaml")
    assert prefs.get("queries")
    assert prefs.get("must_include_any")


def test_score_keeps_agent_job_drops_dropship():
    prefs = load_prefs(ROOT / "data" / "upwork_preferences.yaml")
    jobs = fetch_demo(prefs["queries"])
    scored = {j.job_id: score_job(j, prefs) for j in jobs}
    assert scored["demo-001"].keep
    assert scored["demo-001"].score > scored["demo-002"].score
    assert not scored["demo-002"].keep  # exclude + low pay + entry
    assert scored["demo-003"].keep


def test_exclude_hits():
    prefs = load_prefs(ROOT / "data" / "upwork_preferences.yaml")
    j = JobHit(
        job_id="x",
        title="Crypto trading bot NFT",
        description="make money with crypto trading bot",
        budget_type="hourly",
        budget_min=50,
        budget_max=100,
    )
    s = score_job(j, prefs)
    assert not s.keep

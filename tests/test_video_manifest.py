"""Remotion HHVCTA manifest generator."""

from tools.video_manifest import generate_viral_manifest


def test_benford_manifest_has_scenes_and_fair_report():
    m = generate_viral_manifest("Chicago", "Benfords Law", "Digit 5", "Chicago Open Data")
    assert m["schema"] == "reclaw.video_manifest.v2"
    assert len(m["scenes"]) == 6
    assert m["scenes"][0]["type"] == "HOOK"
    hook = m["scenes"][0]["spoken_script"].lower()
    assert "fraud" not in hook
    assert "benford" in hook or "math" in hook


def test_salary_manifest():
    m = generate_viral_manifest(
        "Gibson",
        "salary_shock",
        "$111K",
        "Indiana Gateway",
        hook_line="Gibson County paid Sheriff $111K",
    )
    assert m["metadata"]["target"] == "Gibson"
    assert m["audio_pipeline"]["tts_provider"] == "elevenlabs"
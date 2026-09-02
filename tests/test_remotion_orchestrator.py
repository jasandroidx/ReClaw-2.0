"""Remotion orchestrator — manifest validation and path helpers."""

import json
from pathlib import Path

import pytest

from tools.remotion_orchestrator import (
    default_output_path,
    manifest_paths_for_county,
    validate_manifest,
    _county_slug,
)
from tools.public_data_loaders import REPO_ROOT


def test_county_slug():
    assert _county_slug("Gibson County") == "gibson"


def test_validate_gibson_manifest():
    path = REPO_ROOT / "data/manifests/gibson/manifest_gibson.json"
    if not path.exists():
        pytest.skip("Gibson manifest not present")
    data = validate_manifest(path)
    assert data.get("schema", "").startswith("reclaw.")


def test_default_output_under_data_renders():
    path = REPO_ROOT / "data/manifests/gibson/manifest_gibson.json"
    if not path.exists():
        pytest.skip("Gibson manifest not present")
    out = default_output_path("Gibson County", path)
    assert "data/renders/gibson" in str(out)
    assert out.suffix == ".mp4"


def test_manifest_paths_for_county():
    paths = manifest_paths_for_county("Gibson")
    if not paths:
        pytest.skip("No Gibson manifests")
    assert all(p.suffix == ".json" for p in paths)


def test_validate_rejects_empty():
    bad = REPO_ROOT / "data/cache/_test_bad_manifest.json"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text(json.dumps({"schema": "other", "foo": 1}), encoding="utf-8")
    try:
        with pytest.raises(ValueError):
            validate_manifest(bad)
    finally:
        bad.unlink(missing_ok=True)
import pytest
import os
from benchmark.run_suite import parse_args, load_config, validate_config_and_args


def test_default_cli_args():
    args = parse_args([])
    assert args.dry_run is True
    assert args.run is False
    assert args.model == ""
    assert args.allow_large_ctx is False


def test_load_default_config():
    config = load_config("benchmark/non_existent_config.yaml")
    assert config["endpoint"] == "http://127.0.0.1:11434"
    assert config["timeout_seconds"] == 120
    assert 2048 in config["context_sizes"]


def test_validate_config_runs_require_model():
    args = parse_args(["--run"])
    config = {"context_sizes": [2048]}
    errors = validate_config_and_args(args, config)
    assert any("explicit model tag" in e for e in errors)
    assert any("ALLOW_OLLAMA_BENCHMARK=true" in e for e in errors)


def test_validate_config_large_context_refusal():
    args = parse_args(["--dry-run"])
    config = {"context_sizes": [2048, 16384]}
    errors = validate_config_and_args(args, config)
    assert any("exceeds safe CPU limit" in e for e in errors)

    # When override flag is supplied
    args_override = parse_args(["--dry-run", "--allow-large-ctx"])
    errors_override = validate_config_and_args(args_override, config)
    assert len(errors_override) == 0

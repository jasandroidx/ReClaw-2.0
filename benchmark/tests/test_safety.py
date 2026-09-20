import pytest
from benchmark.run_suite import check_safety_gate


def test_safety_gate_passes_when_ram_above_threshold():
    config = {"min_free_ram_mb": 2048, "min_free_swap_mb": 512}
    metrics = {
        "total_ram_mb": 8000,
        "free_ram_mb": 4096,
        "total_swap_mb": 2048,
        "free_swap_mb": 1024,
    }
    safe, reason = check_safety_gate(config, metrics)
    assert safe is True
    assert "safety checks passed" in reason.lower()


def test_safety_gate_fails_when_ram_below_threshold():
    config = {"min_free_ram_mb": 2048, "min_free_swap_mb": 512}
    metrics = {
        "total_ram_mb": 8000,
        "free_ram_mb": 1024,  # Below 2048 MB threshold
        "total_swap_mb": 2048,
        "free_swap_mb": 1024,
    }
    safe, reason = check_safety_gate(config, metrics)
    assert safe is False
    assert "below minimum safety threshold" in reason


def test_safety_gate_fails_when_swap_below_threshold():
    config = {"min_free_ram_mb": 2048, "min_free_swap_mb": 512}
    metrics = {
        "total_ram_mb": 8000,
        "free_ram_mb": 4096,
        "total_swap_mb": 2048,
        "free_swap_mb": 256,  # Below 512 MB threshold
    }
    safe, reason = check_safety_gate(config, metrics)
    assert safe is False
    assert "Available Swap" in reason

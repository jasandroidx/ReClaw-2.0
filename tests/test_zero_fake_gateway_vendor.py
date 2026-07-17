"""Zero-fake hard stop: Gateway ent_name must never become vendor drama."""

from tools.split_purchase_detector import detect_split_purchases


def test_split_purchase_returns_empty_on_gateway_by_default():
    """Even for counties with WATER/GAS ent_name rows, no fake vendor flags."""
    flags = detect_split_purchases("Posey", year=2024)
    assert flags == []


def test_split_purchase_still_callable_for_tests_with_override():
    """Opt-in path exists for unit tests of the algorithm only."""
    flags = detect_split_purchases("Posey", year=2024, allow_gateway_ent_name=True)
    # May be empty if cache missing; must not crash
    assert isinstance(flags, list)
    for f in flags:
        assert f.category == "split_purchase"
        # If anything fires, vendor must not be pure rollup denylist leftovers
        desc = f.description.lower()
        assert "governmental activities" not in desc

"""Benford analysis module."""

from tools.benford_analysis import analyze_amounts, leading_digit


def test_leading_digit_strips_currency():
    assert leading_digit("$5,000.00") == "5"
    assert leading_digit("-1234.56") == "1"


def test_natural_benford_like_sample():
    # Synthetic log-uniform-ish amounts
    amounts = [10 ** (i / 50) for i in range(200)]
    result = analyze_amounts(amounts)
    assert result["n"] >= 50
    assert result["verdict"] in ("close_conformity", "acceptable", "marginal", "nonconforming")
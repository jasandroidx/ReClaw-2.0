"""MSU-style fiscal stress from Gateway budget rows."""

from tools.fiscal_health import detect_fiscal_stress


def test_spencer_fiscal_stress_runs():
    flags = detect_fiscal_stress("Spencer", gateway_code=74, year=2025)
    assert isinstance(flags, list)
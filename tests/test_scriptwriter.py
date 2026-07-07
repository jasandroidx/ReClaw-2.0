"""Hook priority and weak-flag filtering for faceless channel scripts."""

from core.handoff import RedFlag
from tools.scriptwriter import (
    _is_publishable,
    _is_weak_dominant,
    _parse_salary_parts,
    _pick_hook,
    _pick_lead_flag,
    build_package,
    build_shorts,
)
from tools.audit_adapter import AuditResult


def _salary_flag(name: str, title: str, amount: int) -> RedFlag:
    return RedFlag(
        severity="high",
        category="salary_shock",
        description=(
            f"{name} — {title} (Circuit Court): ${amount:,} in 2025 public compensation. "
            f"In a county of ~19,935, that's a taxpayer talking-point."
        ),
        evidence="gateway.ifionline.org Employee Compensation export",
    )


def _dominant_flag(line: str, amount: float, *, weak: bool = False) -> RedFlag:
    import json

    return RedFlag(
        severity="critical" if amount >= 5_000_000 else "high",
        category="dominant_disbursement",
        description=(
            f"Spencer County FY2025: '{line}' = ${amount:,.0f} "
            f"(41.3% of $100,000,000 disbursements)"
        ),
        evidence=json.dumps({"amount": amount, "line": line, "source": "gateway"}),
    )


def test_salary_beats_weak_dominant_disbursement():
    flags = [
        _dominant_flag("Other Capital Outlays", 41_300_000, weak=True),
        _salary_flag("Pulley, Thomas", "Referee", 134_988),
    ]
    lead = _pick_lead_flag(flags)
    assert lead is not None
    assert lead.category == "salary_shock"
    hook = _pick_hook(flags, "Spencer County")
    assert "Pulley" in hook
    assert "Referee" in hook
    assert "Other Capital" not in hook


def test_weak_dominant_not_publishable():
    f = _dominant_flag("Other Capital Outlays", 41_300_000, weak=True)
    assert _is_weak_dominant(f)
    assert not _is_publishable(f)


def test_named_fund_dominant_is_publishable():
    f = _dominant_flag("Settlement Fund Disbursements", 35_000_000)
    assert not _is_weak_dominant(f)
    assert _is_publishable(f)


def test_shorts_open_with_named_salary():
    result = AuditResult(
        county="Spencer County",
        red_flags=[
            _dominant_flag("Other Capital Outlays", 41_300_000),
            _salary_flag("Pulley, Thomas", "Referee", 134_988),
        ],
    )
    shorts, _ = build_shorts(result, county="Spencer County")
    assert shorts
    assert "Pulley" in shorts[0]["hook"]
    assert shorts[0]["category"] == "salary_shock"


def test_build_package_top_category_follows_lead():
    result = AuditResult(
        county="Spencer County",
        red_flags=[
            _dominant_flag("Other Capital Outlays", 41_300_000),
            _salary_flag("Heichelbech, Sherri", "Sheriff", 97_280),
        ],
    )
    pkg = build_package(result, county="Spencer County")
    assert pkg["top_category"] == "salary_shock"
    assert "Sheriff" in pkg["top_finding"] or "Heichelbech" in pkg["top_finding"]


def test_parse_salary_parts():
    f = _salary_flag("Pulley, Thomas", "Referee", 134_988)
    name, title = _parse_salary_parts(f)
    assert name == "Pulley, Thomas"
    assert title == "Referee"
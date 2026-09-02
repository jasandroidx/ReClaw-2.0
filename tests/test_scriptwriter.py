"""Hook priority and weak-flag filtering for faceless channel scripts."""

import json

from core.handoff import RedFlag
from tools.scriptwriter import (
    _is_publishable,
    _is_weak_dominant,
    _looks_like_fake_vendor,
    _parse_salary_parts,
    _pick_hook,
    _pick_lead_flag,
    build_package,
    build_shorts,
    long_form_worthiness,
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
    # Viral: not dry recitation
    low = shorts[0]["hook"].lower()
    assert not low.startswith("spencer county paid")


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


def _vendor_flag(category: str, vendor: str, amount: float = 1_000_000) -> RedFlag:
    return RedFlag(
        severity="high",
        category=category,
        description=(
            f"'{vendor}' received ${amount:,.0f} (55.0% of Gibson County FY2025 disbursements)"
            if category == "vendor_concentration"
            else (
                f"Gibson County FY2024: '{vendor}' received 69 disbursements "
                f"each under $50,000, totaling ${amount:,.0f}"
            )
        ),
        evidence=json.dumps(
            {"vendor": vendor, "amount": amount, "total": amount, "tx_count": 69, "source": "gateway"}
        ),
    )


def test_kill_governmental_activities_vendor_concentration():
    f = _vendor_flag("vendor_concentration", "Governmental Activities", 305_000_000)
    assert _looks_like_fake_vendor("Governmental Activities")
    assert not _is_publishable(f)


def test_kill_category_vendor_water_split_purchase():
    f = _vendor_flag("split_purchase", "WATER", 1_200_000)
    assert _looks_like_fake_vendor("WATER")
    assert not _is_publishable(f)


def test_kill_aggregate_payroll_statistical_anomaly():
    f = RedFlag(
        severity="high",
        category="statistical_anomaly",
        description=(
            "Gibson FY2025: disbursement line 'Salaries and Wages' = $12,000,000 "
            "exceeds IQR upper fence"
        ),
        evidence=json.dumps(
            {"amount": 12_000_000, "line": "Salaries and Wages", "method": "IQR_3x"}
        ),
    )
    assert not _is_publishable(f)


def test_kill_weak_disburse_lines_expanded():
    for line in (
        "Transfers Out",
        "Employee Benefits",
        "Payment of Taxes and Other Payroll Withholdings",
        "Distributions to Other Governmental Entities",
        "Other Disbursements",
    ):
        f = _dominant_flag(line, 8_000_000)
        assert not _is_publishable(f), line


def test_real_vendor_split_still_publishable():
    f = _vendor_flag("split_purchase", "ACME Consulting LLC", 312_000)
    assert _is_publishable(f)


def test_shorts_exclude_rollup_and_water():
    result = AuditResult(
        county="Gibson County",
        red_flags=[
            _vendor_flag("vendor_concentration", "Governmental Activities", 305_000_000),
            _vendor_flag("split_purchase", "WATER", 1_200_000),
            _salary_flag("Vanoven, Bruce L", "Sheriff", 111_307),
        ],
    )
    shorts, _ = build_shorts(result, county="Gibson County")
    assert shorts
    assert shorts[0]["category"] == "salary_shock"
    hooks = " ".join(s["hook"] for s in shorts)
    assert "Governmental Activities" not in hooks
    assert "ONE company" not in hooks
    assert "'WATER'" not in hooks
    assert "Vanoven" in shorts[0]["hook"]
    assert "this gibson" not in shorts[0]["hook"].lower()
    assert not shorts[0]["hook"].lower().startswith("gibson county paid")


def test_worthiness_does_not_reward_raw_flag_spam():
    noise = [
        RedFlag(
            severity="high",
            category="statistical_anomaly",
            description=f"line 'Salaries and Wages' outlier #{i}",
            evidence=json.dumps({"amount": 1_000_000 + i, "line": "Salaries and Wages"}),
        )
        for i in range(30)
    ]
    noise.append(_salary_flag("Vanoven, Bruce L", "Sheriff", 111_307))
    result = AuditResult(county="Gibson County", red_flags=noise)
    worthy, score, reasons = long_form_worthiness(result)
    joined = " ".join(reasons).lower()
    assert "30 high-severity" not in joined
    assert "total flags" not in joined or "publishable" in joined
    # Named salary still scores; noise count must not dominate
    assert score < 8 or "named salary" in joined


def test_kill_isolationforest_method_dump():
    f = RedFlag(
        severity="high",
        category="statistical_anomaly",
        description=(
            "Gibson County, IN: GIBSON COUNTY in 2023 → $64,018,300 — "
            "flagged by IsolationForest (Cross-sectional anomaly vs peers)"
        ),
        evidence="DOGEGPT IsolationForest → anomalies_gibson.csv",
    )
    assert not _is_publishable(f)


def test_named_juice_outranks_high_severity_method_noise():
    flags = [
        RedFlag(
            severity="high",
            category="statistical_anomaly",
            description=(
                "Gibson County, IN: GIBSON COUNTY in 2023 → $64,018,300 — "
                "flagged by IsolationForest (Cross-sectional anomaly vs peers)"
            ),
            evidence="DOGEGPT",
        ),
        RedFlag(
            severity="medium",
            category="composition_outlier",
            description="Gibson FY2025: fund 'FIRE PENSION' — 'Purchase of Investments' is 97%",
            evidence=json.dumps(
                {"fund": "FIRE PENSION", "line": "Purchase of Investments", "amount": 4_503_818}
            ),
        ),
        _salary_flag("Vanoven, Bruce L", "Sheriff", 111_307),
    ]
    result = AuditResult(county="Gibson County", red_flags=flags)
    shorts, _ = build_shorts(result, county="Gibson County")
    hooks = " ".join(s["hook"] for s in shorts)
    assert "IsolationForest" not in hooks
    assert "what's weird in the budget" not in hooks.lower()
    assert "Vanoven" in shorts[0]["hook"]
    assert any("FIRE PENSION" in s["hook"] or "double" in s["hook"].lower() or "paycheck" in s["hook"].lower() or "Vanoven" in s["hook"] for s in shorts)
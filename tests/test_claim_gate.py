"""ClaimGate Stage D — actor + $ + contrast + receipt."""

import json

from core.handoff import RedFlag
from tools.claim_gate import evaluate_claim, filter_flags_through_claim_gate, pick_best_claim_ready


def _sboa_ok() -> RedFlag:
    return RedFlag(
        severity="high",
        category="sboa_finding",
        description=(
            "SBOA 84477I p.12 (Clark): Unsupported disbursements of $128,400 "
            "involving Clerk Jane Doe — vs typical clerk peer pay."
        ),
        evidence=json.dumps(
            {
                "report_number": "84477I",
                "page": 12,
                "amount": 128400,
                "name": "Jane Doe",
                "source": "sboa",
                "url": "https://audit.sboa.in.gov/example",
            }
        ),
    )


def _fake_vendor() -> RedFlag:
    return RedFlag(
        severity="critical",
        category="vendor_concentration",
        description="ONE company Governmental Activities got $41,000,000",
        evidence=json.dumps({"entity": "Governmental Activities", "amount": 41_000_000}),
    )


def _salary_with_contrast() -> RedFlag:
    return RedFlag(
        severity="high",
        category="salary_shock",
        description=(
            "Pulley, Thomas — Referee (Circuit Court): $134,988 in 2025 public compensation. "
            "In a county of ~19,935, that's a taxpayer talking-point vs median earnings."
        ),
        evidence="gateway.ifionline.org Employee Compensation export",
    )


def test_sboa_full_claim_passes():
    r = evaluate_claim(_sboa_ok(), county="Clark")
    assert r.ok, r.claim.missing
    assert r.claim.report_id == "84477I"
    assert r.claim.exact_dollar
    assert r.claim.actor


def test_salary_with_contrast_passes():
    r = evaluate_claim(_salary_with_contrast(), county="Spencer")
    assert r.ok, (r.claim.missing, r.claim.to_dict())
    assert "Pulley" in r.claim.actor or "Thomas" in r.claim.actor
    assert r.claim.receipt_path


def test_fake_vendor_fails_actor():
    r = evaluate_claim(_fake_vendor(), county="Gibson")
    assert not r.ok
    assert "named_actor" in r.claim.missing or not r.claim.actor


def test_filter_keeps_only_passers():
    flags = [_fake_vendor(), _sboa_ok(), _salary_with_contrast()]
    kept, results = filter_flags_through_claim_gate(flags, county="Test")
    assert len(results) == 3
    assert all(evaluate_claim(f).ok for f in kept)
    assert len(kept) >= 1


def test_pick_best_prefers_passer():
    flags = [_fake_vendor(), _sboa_ok()]
    lead, res = pick_best_claim_ready(flags, county="Clark")
    assert lead is not None
    assert res is not None
    assert res.ok
    assert lead.category == "sboa_finding"

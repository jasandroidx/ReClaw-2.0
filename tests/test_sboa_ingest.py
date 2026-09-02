"""SBOA ingest — live API discovery (network) + offline finding extract."""

from tools.sboa_ingest import extract_findings_from_text, search_filings


def test_extract_findings_prefers_money_and_skips_letterhead():
    text = """
[page 1]
STATE OF INDIANA AN EQUAL OPPORTUNITY EMPLOYER STATE BOARD OF ACCOUNTS
302 WEST WASHINGTON STREET

[page 9]
RESULTS AND COMMENTS
PAYMENTS TO ACME ENTERPRISES LLC
Investigators found unsupported payments totaling $262,567.35 from the jail commissary fund.
Funds misappropriated, diverted or unaccounted for through malfeasance may be personal obligation.
"""
    findings = extract_findings_from_text(text, source="test.pdf", county="Clark", report_number="84477I")
    assert findings
    joined = " ".join(f["excerpt"] for f in findings)
    assert "262,567" in joined or "$262" in joined
    assert "EQUAL OPPORTUNITY" not in joined


def test_search_filings_clark_returns_special_investigation():
    """Live network: Clark has known special investigation 84477I."""
    rows = search_filings("Clark", unit_types=["county"], page_size=20)
    assert rows
    numbers = {str(r.get("reportNumber") or "") for r in rows}
    # Special investigation present in public index
    assert any(n.upper().endswith("I") for n in numbers) or any(
        "SPECIAL" in str(r.get("auditType") or "").upper() for r in rows
    )

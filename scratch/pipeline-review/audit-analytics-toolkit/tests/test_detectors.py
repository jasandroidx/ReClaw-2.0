"""Every detector is evaluated against the planted ground truth.

The ledger generator plants six classes of control exceptions and records
them in data/ground_truth.csv. These tests assert that each detector
recovers its planted class (high recall) without drowning the file in
false positives.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import audit_tests as at  # noqa: E402
import generate_ledger  # noqa: E402


@pytest.fixture(scope="session")
def data():
    if not (REPO_ROOT / "data" / "journal_entries.csv").exists():
        generate_ledger.main()
    ledger = pd.read_csv(
        REPO_ROOT / "data" / "journal_entries.csv", parse_dates=["posting_ts"]
    )
    users = pd.read_csv(REPO_ROOT / "data" / "users.csv")
    truth = pd.read_csv(REPO_ROOT / "data" / "ground_truth.csv")
    return ledger, users, truth


def planted(truth: pd.DataFrame, anomaly: str) -> set[str]:
    return set(truth[truth.anomaly_type == anomaly].entry_id)


def recall(flagged_ids: set[str], planted_ids: set[str]) -> float:
    return len(flagged_ids & planted_ids) / len(planted_ids)


def test_duplicate_payments_recall(data):
    ledger, _, truth = data
    flagged = set(at.find_duplicate_payments(ledger).entry_id)
    assert recall(flagged, planted(truth, "duplicate_payment")) >= 0.95


def test_threshold_splitting_recall(data):
    ledger, _, truth = data
    flagged = set(at.find_threshold_splitting(ledger).entry_id)
    assert recall(flagged, planted(truth, "threshold_split")) >= 0.90


def test_off_hours_recall_and_batch_exclusion(data):
    ledger, _, truth = data
    result = at.find_off_hours_postings(ledger)
    assert recall(set(result.entry_id), planted(truth, "off_hours")) == 1.0
    assert not (result.posted_by == "BATCH").any()


def test_off_hours_no_false_positives(data):
    """Baseline postings are business-hours weekdays, so everything flagged
    should be planted."""
    ledger, _, truth = data
    flagged = set(at.find_off_hours_postings(ledger).entry_id)
    assert flagged <= planted(truth, "off_hours")


def test_sod_violations_exact(data):
    ledger, users, truth = data
    flagged = set(at.find_sod_violations(ledger, users).entry_id)
    assert flagged == planted(truth, "sod_violation")


def test_round_amounts_flags_planted_vendor(data):
    ledger, _, truth = data
    flagged = set(at.find_round_amounts(ledger).entry_id)
    assert recall(flagged, planted(truth, "round_amount")) >= 0.95


def test_benford_drilldown_isolates_fabricating_vendor(data):
    ledger, _, truth = data
    fabricated = ledger[ledger.entry_id.isin(planted(truth, "benford_vendor"))]
    vendor_id = fabricated.vendor_id.iloc[0]

    ranked = at.benford_by_vendor(ledger)
    assert ranked.iloc[0].vendor_id == vendor_id
    assert ranked.iloc[0].verdict == "nonconformity"


def test_benford_population_flags_contamination_direction(data):
    """The fabricated 7-9 digits should push those observed frequencies
    above Benford expectation."""
    ledger, _, _ = data
    stats = at.benford_first_digit(ledger)
    assert stats["observed"][8] > stats["expected"][8]
    assert stats["observed"][9] > stats["expected"][9]


def test_clean_population_conforms_to_benford(data):
    """With planted entries removed, the ledger should conform (MAD in
    Nigrini's acceptable range) -- i.e. the detectors react to the plants,
    not to generator artefacts."""
    ledger, _, truth = data
    clean = ledger[~ledger.entry_id.isin(set(truth.entry_id))]
    stats = at.benford_first_digit(clean)
    assert stats["mad"] <= 0.012

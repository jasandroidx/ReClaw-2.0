"""Transaction-level detectors for AP register CSVs."""

import tempfile
from pathlib import Path

import pandas as pd

from tools.transaction_anomaly import (
    detect_rule_flags,
    load_transactions,
)


def test_load_and_detect_round_dollar_and_threshold():
    df = pd.DataFrame(
        {
            "Vendor Name": ["Acme Paving", "Acme Paving", "Bob LLC"],
            "Payment Amount": ["$5,000.00", "$49,500.00", "$1,200.00"],
            "Check Date": ["2025-03-15", "2025-06-10", "2025-01-05"],
            "Department": ["Highway", "Highway", "Parks"],
        }
    )
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        df.to_csv(f.name, index=False)
        path = Path(f.name)

    loaded = load_transactions(path)
    assert len(loaded) == 3
    flags = detect_rule_flags(loaded, county="Test")
    cats = {f.category for f in flags}
    assert "round_number_cluster" in cats
    assert "split_purchase" in cats
    path.unlink()
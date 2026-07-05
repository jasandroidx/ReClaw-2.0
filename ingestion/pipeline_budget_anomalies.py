#!/usr/bin/env python3
"""
DOGEGPT budget anomaly pipeline — county budget CSV → anomalies.csv

Uses real Pike data in ingestion/. Run:
  python ingestion/pipeline_budget_anomalies.py
"""

from __future__ import annotations

import csv
from pathlib import Path

INGESTION = Path(__file__).resolve().parent


def load_data(path: str | Path):
    import pandas as pd

    return pd.read_csv(path)


def crosssection_anomalies(df, county_col: str = "county", amount_col: str = "amount"):
    """Flag YoY spikes in department totals (simplified ECOD/IF stand-in)."""
    import pandas as pd

    results = []
    if df.empty:
        return pd.DataFrame(results)

    for (county, dept), grp in df.groupby([county_col, "department"]):
        grp = grp.sort_values("fiscal_year")
        if len(grp) < 2:
            continue
        prev = float(grp.iloc[-2][amount_col])
        curr = float(grp.iloc[-1][amount_col])
        if prev <= 0:
            continue
        pct = (curr - prev) / prev * 100
        if abs(pct) >= 15:
            results.append(
                {
                    "scope": "crosssection_year",
                    "county": county,
                    "department": dept,
                    "category": "",
                    "fiscal_year": int(grp.iloc[-1]["fiscal_year"]),
                    "method": "YoY_spike",
                    "score": round(abs(pct), 2),
                    "pct_change": round(pct, 2),
                    "amount": curr,
                    "prev_amount": prev,
                    "note": f"{pct:+.1f}% YoY change",
                    "script_line": (
                        f"{county}: {dept} budget {pct:+.1f}% YoY "
                        f"(${prev:,.0f} → ${curr:,.0f})"
                    ),
                }
            )
    return pd.DataFrame(results)


def timeseries_anomalies(df, min_years: int = 3):
    """Placeholder for ADTK/time-series — returns empty if no monthly data."""
    import pandas as pd

    return pd.DataFrame()


def main() -> None:
    totals_path = INGESTION / "pike_county_totals_2022_2025.csv"
    out_path = INGESTION / "anomalies.csv"
    if not totals_path.exists():
        raise SystemExit(f"Missing {totals_path}")

    df = load_data(totals_path)
    anomalies = crosssection_anomalies(df)
    if anomalies.empty:
        print("No anomalies detected")
        return

    anomalies.to_csv(out_path, index=False)
    print(f"Wrote {len(anomalies)} anomalies → {out_path}")


if __name__ == "__main__":
    main()
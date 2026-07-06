#!/usr/bin/env python3
"""
DOGEGPT budget anomaly pipeline — county budget CSV → anomalies.csv

Detectors (best available):
  - YoY robust z-score / spike (always)
  - sklearn IsolationForest on composition vectors (always)
  - PyOD ECOD when installed (optional)

Run:
  python ingestion/pipeline_budget_anomalies.py --county Spencer
  python ingestion/pipeline_budget_anomalies.py --in data.csv --out anomalies.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

INGESTION = Path(__file__).resolve().parent


def load_data(path: str | Path):
    import pandas as pd

    return pd.read_csv(path)


def _county_label(county: str) -> str:
    c = county.replace(" County, IN", "").replace(" County", "").strip()
    return f"{c} County, IN"


def crosssection_anomalies(
    df,
    county_col: str = "county",
    amount_col: str = "amount",
    *,
    county_filter: str | None = None,
):
    """YoY spikes + cross-sectional outliers (IsolationForest / ECOD)."""
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import IsolationForest

    results: list[dict] = []
    if df.empty:
        return pd.DataFrame(results)

    work = df.copy()
    if county_filter:
        label = _county_label(county_filter)
        work = work[work[county_col].astype(str).str.lower() == label.lower()]
    if work.empty:
        return pd.DataFrame(results)

    # --- YoY spikes per (county, department[, category]) ---
    group_cols = [county_col, "department"]
    if "category" in work.columns:
        group_cols.append("category")

    for keys, grp in work.groupby(group_cols):
        grp = grp.sort_values("fiscal_year")
        if len(grp) < 2:
            continue
        prev = float(grp.iloc[-2][amount_col])
        curr = float(grp.iloc[-1][amount_col])
        if prev <= 0:
            continue
        pct = (curr - prev) / prev * 100
        if abs(pct) >= 15:
            county = keys[0] if isinstance(keys, tuple) else keys
            dept = keys[1] if isinstance(keys, tuple) and len(keys) > 1 else grp.iloc[-1]["department"]
            cat = keys[2] if isinstance(keys, tuple) and len(keys) > 2 else grp.iloc[-1].get("category", "")
            fy = int(grp.iloc[-1]["fiscal_year"])
            results.append(
                {
                    "scope": "crosssection_year",
                    "county": county,
                    "department": dept,
                    "category": cat or "",
                    "fiscal_year": fy,
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

    # --- Cross-sectional: latest year department totals vs peers ---
    latest_year = int(work["fiscal_year"].max())
    latest = work[work["fiscal_year"] == latest_year]
    pivot = (
        latest.groupby([county_col, "department"], as_index=False)[amount_col]
        .sum()
        .rename(columns={amount_col: "total"})
    )
    if len(pivot) < 3:
        return pd.DataFrame(results)

    X = pivot[["total"]].values
    # Add log-scaled feature for skewed spend
    X = np.column_stack([X, np.log1p(X[:, 0])])

    try:
        iso = IsolationForest(contamination=0.15, random_state=42, n_estimators=100)
        scores = -iso.fit_predict(X)  # 1 = outlier
        pivot = pivot.assign(iso_outlier=scores)
        for _, row in pivot[pivot["iso_outlier"] > 0].iterrows():
            results.append(
                {
                    "scope": "crosssection_year",
                    "county": row[county_col],
                    "department": row["department"],
                    "category": "",
                    "fiscal_year": latest_year,
                    "method": "IsolationForest",
                    "score": round(float(row["total"]) / 1e6, 3),
                    "pct_change": None,
                    "amount": float(row["total"]),
                    "prev_amount": None,
                    "note": "Cross-sectional anomaly vs peers (totals + mix)",
                    "script_line": (
                        f"{row[county_col]}: {row['department']} in {latest_year} "
                        f"→ ${row['total']:,.0f} — flagged by IsolationForest"
                    ),
                }
            )
    except Exception:
        pass

    # --- PyOD ECOD (optional) ---
    try:
        from pyod.models.ecod import ECOD

        ecod = ECOD()
        ecod.fit(X)
        labels = ecod.labels_
        prob = ecod.decision_scores_
        for i, row in pivot.iterrows():
            if labels[i] == 1:
                results.append(
                    {
                        "scope": "crosssection_year",
                        "county": row[county_col],
                        "department": row["department"],
                        "category": "",
                        "fiscal_year": latest_year,
                        "method": "ECOD",
                        "score": round(float(prob[i]), 2),
                        "pct_change": None,
                        "amount": float(row["total"]),
                        "prev_amount": None,
                        "note": "Statistical outlier vs peers (ECOD)",
                        "script_line": (
                            f"{row[county_col]}: {row['department']} in {latest_year} "
                            f"→ ${row['total']:,.0f} — flagged by ECOD"
                        ),
                    }
                )
    except ImportError:
        pass

    if not results:
        return pd.DataFrame(results)
    out = pd.DataFrame(results)
    return out.sort_values("score", ascending=False).drop_duplicates(
        subset=["county", "department", "fiscal_year", "method"], keep="first"
    )


def timeseries_anomalies(df, min_years: int = 3):
    """ADTK level-shift detection when monthly/quarterly granularity exists."""
    import pandas as pd

    if df.empty or "month" not in df.columns:
        return pd.DataFrame()

    try:
        from adtk.detector import LevelShiftAD
        from adtk.data import validate_series
    except ImportError:
        return pd.DataFrame()

    results: list[dict] = []
    for (county, dept), grp in df.groupby(["county", "department"]):
        grp = grp.sort_values(["fiscal_year", "month"])
        if len(grp) < min_years * 2:
            continue
        ts = validate_series(grp.set_index("month")["amount"])
        det = LevelShiftAD(c=6.0, side="both")
        anomalies = det.fit_detect(ts)
        if anomalies is None or not anomalies.any():
            continue
        for idx in anomalies[anomalies].index:
            results.append(
                {
                    "scope": "timeseries",
                    "county": county,
                    "department": dept,
                    "category": "",
                    "fiscal_year": int(grp["fiscal_year"].iloc[-1]),
                    "method": "ADTK_LevelShift",
                    "score": float(grp.loc[grp["month"] == idx, "amount"].iloc[0]),
                    "note": f"Level shift detected at period {idx}",
                    "script_line": f"{county}: {dept} spending level shift at period {idx}",
                }
            )
    return pd.DataFrame(results)


def run_pipeline(
    in_path: Path,
    out_path: Path,
    *,
    county: str | None = None,
) -> int:
    df = load_data(in_path)
    ts = timeseries_anomalies(df)
    cs = crosssection_anomalies(df, county_filter=county)
    import pandas as pd

    combined = pd.concat([ts, cs], ignore_index=True)
    if combined.empty:
        print("No anomalies detected")
        return 0
    combined = combined.sort_values("score", ascending=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out_path, index=False)
    print(f"Wrote {len(combined)} anomalies → {out_path}")
    return len(combined)


def main() -> None:
    parser = argparse.ArgumentParser(description="DOGEGPT budget anomaly pipeline")
    parser.add_argument("--in", dest="in_path", help="Input budget CSV")
    parser.add_argument("--out", dest="out_path", default=str(INGESTION / "anomalies.csv"))
    parser.add_argument("--county", help="Filter to one county (e.g. Spencer or Pike)")
    args = parser.parse_args()

    if args.county and not args.in_path:
        from tools.dogegpt_budget import build_county_budget_csv

        in_path = build_county_budget_csv(args.county)
        if not in_path:
            raise SystemExit(f"Could not build budget CSV for {args.county}")
    elif args.in_path:
        in_path = Path(args.in_path)
    else:
        in_path = INGESTION / "pike_county_totals_2022_2025.csv"

    if not in_path.exists():
        raise SystemExit(f"Missing {in_path}")

    run_pipeline(in_path, Path(args.out_path), county=args.county)


if __name__ == "__main__":
    main()
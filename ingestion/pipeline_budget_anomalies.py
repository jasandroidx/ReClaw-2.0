#!/usr/bin/env python
"""
DOGEGPT – Budget Anomaly Pipeline
Run on a CSV of budget line items to emit anomalies.csv suitable for watchdog scripts.

Usage:
  python pipeline_budget_anomalies.py --in data/pike_budget.csv --out output/anomalies.csv --county "Pike County, IN"
Optional:
  --min_years 3        # require at least this many years per (dept, category) to run timeseries checks
  --seed 42
"""
import argparse, sys, os, math, warnings
from pathlib import Path

import pandas as pd
import numpy as np

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

# Optional imports
try:
    from pyod.models.ecod import ECOD
    HAVE_ECOD = True
except Exception:
    HAVE_ECOD = False

try:
    from adtk.detector import LevelShiftAD, PersistAD, SeasonalAD, VolatilityShiftAD
    from adtk.data import validate_series
    HAVE_ADTK = True
except Exception:
    HAVE_ADTK = False

warnings.filterwarnings("ignore")

def robust_z(x):
    x = pd.Series(x).astype(float)
    med = x.median()
    mad = (x - med).abs().median()
    if mad == 0 or np.isnan(mad):
        return pd.Series([0]*len(x), index=x.index, dtype=float)
    return 0.6745 * (x - med) / mad

def percent_change(curr, prev):
    try:
        if prev == 0 or pd.isna(prev):
            return np.nan
        return 100.0 * (curr - prev) / abs(prev)
    except Exception:
        return np.nan

def load_data(path):
    df = pd.read_csv(path) if path.lower().endswith(".csv") else pd.read_excel(path)
    # normalize columns (case-insensitive)
    cols = {c.lower().strip(): c for c in df.columns}
    def pick(*names):
        for n in names:
            if n in cols: return cols[n]
        return None
    mapping = {
        'county': pick('county'),
        'fiscal_year': pick('fiscal_year','year'),
        'month': pick('month','mo'),
        'department': pick('department','dept'),
        'category': pick('category','acct_category','object'),
        'account_code': pick('account_code','gl_code','account','acct'),
        'vendor': pick('vendor','payee'),
        'description': pick('description','memo','detail','desc'),
        'amount': pick('amount','amt','value','usd')
    }
    missing = [k for k,v in mapping.items() if v is None and k in ('fiscal_year','department','amount')]
    if missing:
        raise ValueError(f"Missing required columns (case-insensitive): {missing}")
    # rename
    rmap = {v:k for k,v in mapping.items() if v is not None}
    df = df.rename(columns=rmap)
    # types
    if 'fiscal_year' in df: df['fiscal_year'] = pd.to_numeric(df['fiscal_year'], errors='coerce')
    if 'month' in df and df['month'].notna().any(): df['month'] = pd.to_numeric(df['month'], errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
    # drop empties
    df = df.dropna(subset=['fiscal_year','department'])
    df = df[df['amount'].notna()]
    # normalize strings
    for col in ['county','department','category','account_code','vendor','description']:
        if col in df:
            df[col] = df[col].astype(str).str.strip()
    return df

def timeseries_anomalies(df, min_years=3):
    """Return DataFrame of anomalies found in per-(dept, category) series across years (and months if present)."""
    results = []
    has_month = 'month' in df.columns and df['month'].notna().any()
    keys = ['department'] + (['category'] if 'category' in df.columns else [])
    group_cols = keys + (['month'] if has_month else [])
    agg = df.groupby(['fiscal_year'] + group_cols, dropna=False)['amount'].sum().reset_index()
    # z-score & YoY
    for key_vals, sub in agg.groupby(keys, dropna=False):
        sub = sub.sort_values(['fiscal_year'] + (['month'] if has_month else []))
        years = sub['fiscal_year'].nunique()
        if years < min_years:
            continue
        # annual rollup too (even if monthly exists)
        annual = sub.groupby('fiscal_year')['amount'].sum().reset_index()
        annual['robust_z'] = robust_z(annual['amount'])
        annual['prev_amount'] = annual['amount'].shift(1)
        annual['pct_change'] = annual.apply(lambda r: percent_change(r['amount'], r['prev_amount']), axis=1)
        for _,r in annual.iterrows():
            yoy_flag = not pd.isna(r['pct_change']) and abs(r['pct_change']) >= 8
            if abs(r['robust_z']) >= 3 or (not pd.isna(r['pct_change']) and abs(r['pct_change'])>=50) or yoy_flag:
                rec = {
                    'scope':'timeseries_annual',
                    'department': key_vals if isinstance(key_vals,str) else key_vals[0],
                    'category': None if isinstance(key_vals,str) else (key_vals[1] if len(key_vals)>1 else None),
                    'fiscal_year': int(r['fiscal_year']),
                    'method':'robust_z|pct_change',
                    'score': float(abs(r['robust_z'])) if not pd.isna(r['robust_z']) else 0.0,
                    'pct_change': float(r['pct_change']) if not pd.isna(r['pct_change']) else None,
                    'amount': float(r['amount']),
                    'prev_amount': float(r['prev_amount']) if not pd.isna(r['prev_amount']) else None,
                    'note':'Annual spike vs history'
                }
                results.append(rec)
        # monthly ADTK if available
        if has_month and HAVE_ADTK:
            subm = sub.pivot(index='fiscal_year', columns='month', values='amount').fillna(0.0)
            # Flatten yearly vector to detect level shifts across months (simple diff)
            # ADTK is stronger on regular DateTimeIndex; here we do robust stats across months.
            month_tot = sub.groupby('fiscal_year')['amount'].sum().sort_index()
            s = pd.Series(month_tot)
            s.index = pd.PeriodIndex(s.index, freq='Y').to_timestamp()
            series = validate_series(s)
            detectors = {
                'LevelShiftAD': LevelShiftAD(window=2, c=6.0),
                'PersistAD': PersistAD(window=3, c=3.0),
                'VolatilityShiftAD': VolatilityShiftAD(window=3, c=3.0)
            }
            for name,det in detectors.items():
                try:
                    anom = det.fit_detect(series)
                    for ts, flag in anom.items():
                        if bool(flag):
                            fy = int(ts.year)
                            amt = float(month_tot.loc[fy]) if fy in month_tot.index else None
                            results.append({
                                'scope':'timeseries_monthly',
                                'department': key_vals if isinstance(key_vals,str) else key_vals[0],
                                'category': None if isinstance(key_vals,str) else (key_vals[1] if len(key_vals)>1 else None),
                                'fiscal_year': fy,
                                'method': f'ADTK:{name}',
                                'score': 1.0,
                                'pct_change': None,
                                'amount': amt,
                                'prev_amount': None,
                                'note': f'{name} flagged structural change'
                            })
                except Exception:
                    pass
    return pd.DataFrame(results)

def crosssection_anomalies(df):
    """Detect anomalies within each fiscal_year across departments using totals & composition features."""
    records = []
    # Build per-year x per-department table of totals by category (wide)
    base = df.copy()
    base['category'] = base.get('category','Unspecified').fillna('Unspecified')
    for fy, sub in base.groupby('fiscal_year'):
        # pivot to department x category matrix
        mat = sub.pivot_table(index='department', columns='category', values='amount', aggfunc='sum', fill_value=0.0)
        # features: totals + composition ratios
        totals = mat.sum(axis=1).rename('total')
        comp = mat.div(totals.replace(0,np.nan), axis=0).fillna(0.0)
        X = pd.concat([totals, comp], axis=1)
        # scale robustly
        scaler = RobustScaler()
        Xs = pd.DataFrame(scaler.fit_transform(X), index=X.index, columns=X.columns)
        # Isolation Forest
        iso = IsolationForest(n_estimators=300, contamination='auto', random_state=42)
        iso.fit(Xs)
        iso_score = -iso.score_samples(Xs)  # higher = more anomalous
        year_df = pd.DataFrame({
            'fiscal_year': int(fy),
            'department': Xs.index,
            'method': 'IsolationForest',
            'score': iso_score,
            'amount': totals.values,
            'note': 'Cross-sectional anomaly vs peers (totals + mix)'
        })
        records.append(year_df)
        # ECOD (if available)
        if HAVE_ECOD:
            ec = ECOD()
            ec.fit(Xs.values)
            ec_score = ec.decision_scores_
            rec2 = pd.DataFrame({
                'fiscal_year': int(fy),
                'department': Xs.index,
                'method': 'ECOD',
                'score': ec_score,
                'amount': totals.values,
                'note': 'Statistical outlier vs peers (ECOD)'
            })
            records.append(rec2)
    out = pd.concat(records, ignore_index=True) if records else pd.DataFrame(columns=['fiscal_year','department','method','score','amount','note'])
    # Flag top-k by method per year (e.g., top 5)
    flagged = []
    for (fy, m), g in out.groupby(['fiscal_year','method']):
        k = max(1, int(0.05*len(g)))  # top 5%
        flagged.append(g.sort_values('score', ascending=False).head(k))
    flagged = pd.concat(flagged, ignore_index=True) if flagged else out
    flagged['scope'] = 'crosssection_year'
    flagged['category'] = None
    flagged['pct_change'] = None
    flagged['prev_amount'] = None
    return flagged

def _county_label(county: str) -> str:
    c = county.replace(" County, IN", "").replace(" County", "").strip()
    return f"{c} County, IN" if c else ""


def run_pipeline(
    in_path: str | Path,
    out_path: str | Path,
    *,
    county: str | None = None,
    min_years: int = 3,
) -> int:
    """Programmatic entry used by tools/dogegpt_budget.py and red_flag_engine."""
    inp = str(in_path)
    outp = str(out_path)
    county_label = _county_label(county) if county else ""
    os.makedirs(os.path.dirname(outp) or ".", exist_ok=True)

    df = load_data(inp)
    if county_label:
        df["county"] = county_label
    df = df[df["amount"] >= 0]
    ts = timeseries_anomalies(df, min_years=min_years)
    cs = crosssection_anomalies(df)
    cols = [
        "scope", "county", "department", "category", "fiscal_year",
        "method", "score", "pct_change", "amount", "prev_amount", "note",
    ]
    for d in (ts, cs):
        if "county" not in d.columns:
            d["county"] = df["county"].iloc[0] if "county" in df.columns and len(df["county"].dropna()) else ""
        for c in cols:
            if c not in d.columns:
                d[c] = None
        d["score"] = pd.to_numeric(d["score"], errors="coerce")
        d["amount"] = pd.to_numeric(d["amount"], errors="coerce")
        d["prev_amount"] = pd.to_numeric(d["prev_amount"], errors="coerce")
        d["pct_change"] = pd.to_numeric(d["pct_change"], errors="coerce")
    out = pd.concat([ts[cols], cs[cols]], ignore_index=True).sort_values(
        ["fiscal_year", "score"], ascending=[True, False]
    )

    def fmt_currency(x):
        try:
            return "${:,.0f}".format(float(x))
        except Exception:
            return ""

    out["script_line"] = out.apply(
        lambda r: f"{r.get('county', '')}: {r.get('department', '')}"
        + (f" / {r.get('category')}" if r.get("category") else "")
        + f" in {int(r['fiscal_year']) if not pd.isna(r['fiscal_year']) else 'N/A'} → "
        + (f"{fmt_currency(r['amount'])}" if not pd.isna(r["amount"]) else "amount N/A")
        + (f" ({r['pct_change']:.0f}% YoY)" if not pd.isna(r["pct_change"]) else "")
        + f" — flagged by {r['method']} ({r['note']})",
        axis=1,
    )
    out.to_csv(outp, index=False)
    return len(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", help="Input CSV/XLSX path")
    ap.add_argument("--out", dest="outp", default="ingestion/anomalies.csv", help="Output CSV for anomalies")
    ap.add_argument("--county", dest="county", default="", help="County name (builds Gateway CSV if --in omitted)")
    ap.add_argument("--min_years", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if args.county and not args.inp:
        import sys
        from pathlib import Path

        repo = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(repo))
        from tools.dogegpt_budget import build_county_budget_csv

        built = build_county_budget_csv(args.county)
        if not built:
            raise SystemExit(f"Could not build budget CSV for {args.county}")
        args.inp = str(built)
        if args.outp == "ingestion/anomalies.csv":
            args.outp = str(Path(__file__).parent / f"anomalies_{args.county.lower()}.csv")

    if not args.inp:
        ap.error("--in required unless --county is provided")

    n = run_pipeline(args.inp, args.outp, county=args.county or None, min_years=args.min_years)
    print(f"Wrote anomalies → {args.outp}  | rows={n}")


if __name__ == "__main__":
    main()

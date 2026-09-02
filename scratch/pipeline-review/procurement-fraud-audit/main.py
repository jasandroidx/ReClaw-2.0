"""
Runnable entry point for the forensic procurement audit demo.

Usage:
    python main.py path/to/payments.csv --threshold 500000 --window 7D

If no CSV is given, a synthetic dataset with planted fraud patterns is generated
so the pipeline is demonstrable out of the box.
"""
import argparse
import sys

import numpy as np
import pandas as pd

import audit


def make_demo_data(n: int = 100_000, seed: int = 42) -> pd.DataFrame:
    """Synthetic payments with planted duplicate-within-7-days fraud rings."""
    rng = np.random.default_rng(seed)
    base = pd.Timestamp("2025-01-01")
    df = pd.DataFrame(
        {
            "vendor_id": rng.integers(1, 2000, n).astype(str),
            "vendor_name": ["Vendor_" + str(v) for v in rng.integers(1, 2000, n)],
            "payment_date": base + pd.to_timedelta(rng.integers(0, 365, n), unit="D"),
            "amount": rng.gamma(2.0, 50_000, n).round(2),
            "bank_account": ["ACC" + str(a) for a in rng.integers(1, 1800, n)],
        }
    )
    # Plant a fraud ring: vendor 9999 paid 3x in one week, sum > R500k
    ring = pd.DataFrame(
        {
            "vendor_id": ["9999"] * 3,
            "vendor_name": ["ACME Trading", "Acme  Trading", "ACME-TRADING"],
            "payment_date": [base, base + pd.Timedelta("2D"), base + pd.Timedelta("5D")],
            "amount": [240_000, 180_000, 150_000],
            "bank_account": ["ACC777", "ACC777", "ACC777"],
        }
    )
    return pd.concat([df, ring], ignore_index=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Forensic procurement audit")
    ap.add_argument("csv", nargs="?", help="payments CSV (omit for demo data)")
    ap.add_argument("--threshold", type=float, default=500_000)
    ap.add_argument("--window", default="7D")
    ap.add_argument("--approval-limit", type=float, default=100_000)
    args = ap.parse_args(argv)

    if args.csv:
        df = audit.load_payments(args.csv)
        for r in df.attrs.get("repairs", []):
            print(f"  [data-quality] {r}")
    else:
        print("No CSV provided — generating 100k-row synthetic demo dataset.")
        df = make_demo_data()

    df = audit.normalize_vendors(df)

    dup = audit.rolling_window_flags(df, args.window, args.threshold)
    split = audit.split_payment_flags(df, args.approval_limit)
    rnd = audit.round_number_flags(df)
    shared = audit.duplicate_bank_account_flags(df)
    benford = audit.benford_first_digit(df)

    print("\n===== FORENSIC PROCUREMENT AUDIT — FINDINGS =====")
    print(f"Rows audited:                 {len(df):,}")
    print(f"Rolling {args.window} >{args.threshold:,.0f} duplicate flags: {len(dup):,}")
    print(f"Split-payment (threshold gaming) flags: {len(split):,}")
    print(f"Round-number flags:           {len(rnd):,}")
    print(f"Shared-bank-account rows:     {len(shared):,}")
    print(f"Benford max abs deviation:    {benford['abs_dev'].max():.3f}")

    if len(dup):
        print("\nTop duplicate-window flags (vendor / window sum / count):")
        cols = ["vendor_id", "vendor_name", "payment_date", "amount", "w_sum", "w_cnt"]
        print(dup.sort_values("w_sum", ascending=False)[cols].head(10).to_string(index=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())

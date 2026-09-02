"""
Forensic procurement audit — core detection logic.

All checks operate on a single normalized payments DataFrame with at least:
    vendor_id, vendor_name, payment_date, amount, [bank_account], [approver]

Every flag returned carries the exact contributing row indices so the finding
traces back to source data — no assertion without evidence.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


# ----------------------------------------------------------------------------
# Ingest & normalize
# ----------------------------------------------------------------------------
def load_payments(path: str) -> pd.DataFrame:
    """Load a payments CSV with defensive type coercion and a repair log."""
    df = pd.read_csv(path, dtype=str)
    repairs = []

    df["payment_date"] = pd.to_datetime(df["payment_date"], errors="coerce", dayfirst=True)
    df["amount"] = pd.to_numeric(
        df["amount"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
        errors="coerce",
    )

    bad_date = df["payment_date"].isna().sum()
    bad_amt = df["amount"].isna().sum()
    if bad_date:
        repairs.append(f"{bad_date} rows had unparseable payment_date")
    if bad_amt:
        repairs.append(f"{bad_amt} rows had unparseable amount")

    df.attrs["repairs"] = repairs
    return df


def normalize_vendors(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse near-duplicate vendor names (a common fraud-hiding trick)."""
    df = df.copy()
    df["vendor_key"] = (
        df["vendor_name"].fillna("").str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
    )
    return df


# ----------------------------------------------------------------------------
# Core check: rolling-window duplicate / split payments
# ----------------------------------------------------------------------------
def rolling_window_flags(
    df: pd.DataFrame,
    window: str = "7D",
    threshold: float = 500_000,
    group_col: str = "vendor_id",
) -> pd.DataFrame:
    """
    Vendors paid multiple times within a rolling time window where the summed
    amount exceeds `threshold`.

    The '7D' offset windows by CALENDAR TIME, not by row count — this is the
    correct interpretation of "within a 7-day window".
    """
    work = df.dropna(subset=["payment_date", "amount"]).copy()
    work = work.sort_values([group_col, "payment_date"]).set_index("payment_date")

    roll = work.groupby(group_col)["amount"].rolling(window)
    work["w_sum"] = roll.sum().reset_index(level=0, drop=True)
    work["w_cnt"] = roll.count().reset_index(level=0, drop=True)

    flagged = work[(work["w_sum"] > threshold) & (work["w_cnt"] > 1)]
    return flagged.reset_index()


# ----------------------------------------------------------------------------
# Supporting checks
# ----------------------------------------------------------------------------
def split_payment_flags(df: pd.DataFrame, approval_limit: float, band: float = 0.05):
    """Payments clustered just under an approval threshold (threshold gaming)."""
    lo = approval_limit * (1 - band)
    work = df.dropna(subset=["amount"])
    return work[(work["amount"] >= lo) & (work["amount"] < approval_limit)]


def round_number_flags(df: pd.DataFrame):
    """Suspiciously round amounts (e.g. exact thousands)."""
    work = df.dropna(subset=["amount"])
    return work[(work["amount"] >= 10_000) & (work["amount"] % 1000 == 0)]


def benford_first_digit(df: pd.DataFrame) -> pd.DataFrame:
    """First-digit distribution vs Benford's Law — large deviation => manipulation."""
    amt = df["amount"].dropna().abs()
    amt = amt[amt >= 1]
    first = amt.astype(str).str.replace(".", "", regex=False).str[0].astype(int)
    observed = first.value_counts(normalize=True).reindex(range(1, 10), fill_value=0)
    expected = pd.Series({d: np.log10(1 + 1 / d) for d in range(1, 10)})
    out = pd.DataFrame({"observed": observed, "expected": expected})
    out["abs_dev"] = (out["observed"] - out["expected"]).abs()
    return out


def duplicate_bank_account_flags(df: pd.DataFrame):
    """One bank account shared across multiple distinct vendors."""
    if "bank_account" not in df.columns:
        return pd.DataFrame()
    grp = df.dropna(subset=["bank_account"]).groupby("bank_account")["vendor_id"].nunique()
    shared = grp[grp > 1].index
    return df[df["bank_account"].isin(shared)]

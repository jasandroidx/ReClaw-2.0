"""Computer-assisted audit techniques (CAATs) for journal-entry testing.

Each detector is a pure function over the ledger DataFrame that returns the
flagged entries. The tests mirror the standard journal-entry testing
procedures auditors apply when addressing fraud risk (ISA 240):

    benford_first_digit      digit-frequency analysis (population + per vendor)
    find_duplicate_payments  same vendor + amount within a short window
    find_threshold_splitting invoice clusters just under the approval limit
    find_off_hours_postings  nights / weekends by human users
    find_sod_violations      poster == approver, or approver lacks the right
    find_round_amounts       vendors with excessive round-thousand amounts
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Expected Benford first-digit frequencies: log10(1 + 1/d).
BENFORD_EXPECTED = {d: np.log10(1 + 1 / d) for d in range(1, 10)}

# Nigrini's mean-absolute-deviation conformity bands for first digits.
MAD_BANDS = [
    (0.006, "close conformity"),
    (0.012, "acceptable conformity"),
    (0.015, "marginal conformity"),
    (np.inf, "nonconformity"),
]


def first_digit(amounts: pd.Series) -> pd.Series:
    return amounts.abs().astype(str).str.lstrip("0.").str[0].astype(int)


def benford_first_digit(ledger: pd.DataFrame) -> dict:
    """Population-level Benford analysis of first digits.

    Returns observed vs expected frequencies, the chi-square statistic and
    Nigrini's MAD. MAD is the primary conformity verdict: with tens of
    thousands of entries, chi-square rejects even trivial deviations
    (its statistic scales with n), while MAD is sample-size independent.
    """
    digits = first_digit(ledger["amount_rm"])
    observed = digits.value_counts(normalize=True).reindex(range(1, 10), fill_value=0.0)
    expected = pd.Series(BENFORD_EXPECTED)
    n = len(digits)
    chi_square = float((n * (observed - expected) ** 2 / expected).sum())
    mad = float((observed - expected).abs().mean())
    verdict = next(label for cutoff, label in MAD_BANDS if mad <= cutoff)
    return {
        "observed": observed,
        "expected": expected,
        "n": n,
        "chi_square": chi_square,
        "mad": mad,
        "verdict": verdict,
    }


def benford_by_vendor(ledger: pd.DataFrame, min_entries: int = 100) -> pd.DataFrame:
    """Per-vendor MAD drill-down; vendors ranked most-deviant first."""
    results = []
    for (vendor_id, vendor_name), grp in ledger.groupby(["vendor_id", "vendor_name"]):
        if len(grp) < min_entries:
            continue
        stats = benford_first_digit(grp)
        results.append(
            {
                "vendor_id": vendor_id,
                "vendor_name": vendor_name,
                "n_entries": len(grp),
                "mad": round(stats["mad"], 4),
                "verdict": stats["verdict"],
            }
        )
    return (
        pd.DataFrame(results)
        .sort_values("mad", ascending=False)
        .reset_index(drop=True)
    )


def find_duplicate_payments(ledger: pd.DataFrame, window_days: int = 7) -> pd.DataFrame:
    """Same vendor and exact amount posted more than once within the window."""
    df = ledger.sort_values("posting_ts").copy()
    df["prev_ts"] = df.groupby(["vendor_id", "amount_rm"])["posting_ts"].shift(1)
    gap = (df["posting_ts"] - df["prev_ts"]).dt.total_seconds() / 86_400
    dup_second = df[gap.le(window_days)]
    # include the first occurrence of each duplicated (vendor, amount) pair
    keys = set(map(tuple, dup_second[["vendor_id", "amount_rm"]].to_numpy()))
    mask = df[["vendor_id", "amount_rm"]].apply(tuple, axis=1).isin(keys)
    return (
        df[mask]
        .drop(columns="prev_ts")
        .sort_values(["vendor_id", "amount_rm", "posting_ts"])
    )


def find_threshold_splitting(
    ledger: pd.DataFrame,
    threshold_rm: float = 50_000.0,
    band: float = 0.10,
    window_days: int = 7,
) -> pd.DataFrame:
    """Clusters of invoices each just under the approval threshold.

    Flags groups of >= 2 invoices from the same vendor posted by the same
    user within the window, each within `band` below the threshold, whose
    combined value exceeds the threshold -- the signature of a purchase
    split to dodge a higher approval level.
    """
    near = ledger[
        ledger["amount_rm"].between(threshold_rm * (1 - band), threshold_rm - 0.01)
    ].sort_values("posting_ts")

    flagged: list[pd.DataFrame] = []
    for _, grp in near.groupby(["vendor_id", "posted_by"]):
        if len(grp) < 2:
            continue
        # slide the window over every entry so clusters are found regardless
        # of unrelated near-threshold invoices earlier in the year
        for anchor in grp["posting_ts"]:
            in_window = (grp["posting_ts"] >= anchor) & (
                (grp["posting_ts"] - anchor).dt.days <= window_days
            )
            cluster = grp[in_window]
            if len(cluster) >= 2 and cluster["amount_rm"].sum() > threshold_rm:
                flagged.append(cluster)
    if not flagged:
        return ledger.iloc[0:0]
    return pd.concat(flagged).drop_duplicates(subset="entry_id")


def find_off_hours_postings(
    ledger: pd.DataFrame,
    night_start: int = 22,
    night_end: int = 6,
    exclude_users: tuple[str, ...] = ("BATCH",),
) -> pd.DataFrame:
    """Entries posted on weekends or between night_start and night_end by
    human users (system batch accounts excluded)."""
    ts = ledger["posting_ts"]
    is_weekend = ts.dt.weekday >= 5
    is_night = (ts.dt.hour >= night_start) | (ts.dt.hour < night_end)
    is_human = ~ledger["posted_by"].isin(exclude_users)
    return ledger[(is_weekend | is_night) & is_human]


def find_sod_violations(ledger: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
    """Self-approved entries, or approvals by users without approval rights."""
    rights = users.set_index("user_id")["can_approve"]
    self_approved = ledger["posted_by"] == ledger["approved_by"]
    unauthorised = ~ledger["approved_by"].map(rights).fillna(False).astype(bool)
    return ledger[self_approved | unauthorised]


def find_round_amounts(
    ledger: pd.DataFrame,
    round_to: int = 1_000,
    rate_multiple: float = 5.0,
    min_round_entries: int = 10,
) -> pd.DataFrame:
    """Vendors whose rate of exactly-round amounts is far above the norm.

    A handful of round invoices is normal (retainers, deposits), so the
    benchmark is the population's own round-amount rate: a vendor is flagged
    when its rate is at least `rate_multiple` times that benchmark with a
    material number of round entries.
    """
    df = ledger.copy()
    df["is_round"] = (df["amount_rm"] % round_to == 0) & (df["amount_rm"] > 0)
    population_rate = max(float(df["is_round"].mean()), 0.001)
    by_vendor = df.groupby("vendor_id")["is_round"].agg(["mean", "sum"])
    suspect = by_vendor[
        (by_vendor["mean"] >= rate_multiple * population_rate)
        & (by_vendor["sum"] >= min_round_entries)
    ]
    return df[df["vendor_id"].isin(suspect.index) & df["is_round"]].drop(columns="is_round")

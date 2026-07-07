"""
Transaction-level anomaly detection for county AP registers / GL detail.

Use when a county publishes check registers with vendor + date + amount.
Indiana Gateway disbursements lack payment_date and payee vendor — run
tools.procurement_detectors + red_flag_engine for Gateway instead.

Returns repo-native RedFlag objects for scriptwriter / county queue.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from core.handoff import RedFlag

# Common column aliases in county exports
_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "vendor": ("vendor", "payee", "vendor_name", "entity", "ent_name", "name"),
    "amount": ("amount", "payment", "payment_amount", "check_amount", "total"),
    "date": ("date", "payment_date", "check_date", "posting_date", "trans_date"),
    "department": ("department", "dept", "dept_code", "fund", "fund_name", "account"),
    "invoice": ("invoice", "invoice_no", "invoice_number", "check_no", "check_number"),
}

APPROVAL_THRESHOLD = 50_000
CONCENTRATION_PCT = 0.40


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    lower = {c: c.strip().lower().replace(" ", "_") for c in df.columns}
    df = df.rename(columns=lower)
    mapping: dict[str, str] = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                mapping[alias] = canonical
                break
    return df.rename(columns=mapping)


def load_transactions(path: str | Path) -> pd.DataFrame:
    """Load CSV/Excel AP register; normalize to vendor/amount/date/department/invoice."""
    path = Path(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    df = _normalize_columns(df)
    if "amount" not in df.columns:
        raise ValueError("No amount column found — expected amount/payment/check_amount")
    df["amount"] = pd.to_numeric(
        df["amount"].astype(str).str.replace(r"[$,]", "", regex=True),
        errors="coerce",
    )
    df = df.dropna(subset=["amount"])
    df = df[df["amount"] > 0].copy()
    if "vendor" not in df.columns:
        df["vendor"] = "unknown"
    df["vendor"] = df["vendor"].astype(str).str.strip()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.reset_index(drop=True)


def _row_provenance(row: pd.Series, *, extra: dict | None = None) -> str:
    payload = {
        "vendor": str(row.get("vendor", ""))[:120],
        "amount": float(row["amount"]),
        "date": row["date"].strftime("%Y-%m-%d") if pd.notna(row.get("date")) else None,
        "department": str(row.get("department", ""))[:80],
        "invoice": str(row.get("invoice", ""))[:40],
        "row_index": int(row.name) if row.name is not None else None,
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload)


def detect_rule_flags(
    df: pd.DataFrame,
    *,
    county: str = "County",
    approval_threshold: float = APPROVAL_THRESHOLD,
    concentration_pct: float = CONCENTRATION_PCT,
    max_flags: int = 30,
) -> list[RedFlag]:
    """Rule-based red flags — ISA 240 style smoke tests with row provenance."""
    flags: list[RedFlag] = []

    # Round-dollar payments
    for idx, row in df.iterrows():
        amt = float(row["amount"])
        if amt >= 5_000 and amt % 1_000 == 0:
            flags.append(
                RedFlag(
                    severity="medium",
                    category="round_number_cluster",
                    description=(
                        f"{county}: round-dollar payment ${amt:,.0f} to "
                        f"'{row['vendor']}' — common audit sample trigger"
                    ),
                    evidence=_row_provenance(row, extra={"rule": "round_dollar"}),
                    recommended_action="Request supporting invoice and approval chain.",
                )
            )

    # Just under bid threshold
    for idx, row in df.iterrows():
        amt = float(row["amount"])
        if approval_threshold * 0.95 <= amt < approval_threshold:
            flags.append(
                RedFlag(
                    severity="high",
                    category="split_purchase",
                    description=(
                        f"{county}: payment ${amt:,.0f} to '{row['vendor']}' sits just under "
                        f"${approval_threshold:,.0f} approval threshold (IC 36-1-12-19 pattern)"
                    ),
                    evidence=_row_provenance(row, extra={"rule": "under_threshold"}),
                    recommended_action="Check for split purchases same vendor/FY.",
                )
            )

    # Weekend / holiday payments (when dates present)
    if "date" in df.columns and df["date"].notna().any():
        weekend = df[df["date"].dt.dayofweek >= 5]
        for idx, row in weekend.head(15).iterrows():
            flags.append(
                RedFlag(
                    severity="medium",
                    category="statistical_anomaly",
                    description=(
                        f"{county}: weekend payment ${float(row['amount']):,.0f} to "
                        f"'{row['vendor']}' on {row['date'].strftime('%Y-%m-%d')}"
                    ),
                    evidence=_row_provenance(row, extra={"rule": "weekend_payment"}),
                    recommended_action="Verify emergency vs routine AP posting.",
                )
            )

        # Duplicate vendor + amount + date
        key_cols = ["vendor", "amount", "date"]
        dupes = df[df.duplicated(subset=key_cols, keep=False)].sort_values(key_cols)
        seen: set[tuple] = set()
        for idx, row in dupes.iterrows():
            key = (row["vendor"], float(row["amount"]), row["date"])
            if key in seen:
                continue
            seen.add(key)
            flags.append(
                RedFlag(
                    severity="high",
                    category="statistical_anomaly",
                    description=(
                        f"{county}: duplicate payment ${float(row['amount']):,.0f} to "
                        f"'{row['vendor']}' on {row['date'].strftime('%Y-%m-%d')}"
                    ),
                    evidence=_row_provenance(row, extra={"rule": "duplicate_vendor_amount_date"}),
                    recommended_action="Match to invoice numbers; check for double pay.",
                )
            )

    # Vendor concentration by department
    if "department" in df.columns:
        for dept, grp in df.groupby("department"):
            total = grp["amount"].sum()
            if total < 100_000:
                continue
            top_vendor, top_amt = grp.groupby("vendor")["amount"].sum().idxmax(), 0.0
            top_amt = float(grp.groupby("vendor")["amount"].sum().max())
            share = top_amt / total
            if share >= concentration_pct:
                flags.append(
                    RedFlag(
                        severity="high" if share >= 0.5 else "medium",
                        category="vendor_concentration",
                        description=(
                            f"{county}: '{top_vendor}' received {share*100:.0f}% of "
                            f"'{dept}' spend (${top_amt:,.0f} / ${total:,.0f})"
                        ),
                        evidence=json.dumps(
                            {
                                "vendor": top_vendor[:120],
                                "department": str(dept)[:80],
                                "share": round(share, 3),
                                "amount": top_amt,
                                "rule": "dept_concentration",
                            }
                        ),
                        recommended_action="Confirm competitive bidding for concentrated vendor.",
                    )
                )

    return flags[:max_flags]


def detect_isolation_forest(
    df: pd.DataFrame,
    *,
    county: str = "County",
    contamination: float = 0.05,
    max_flags: int = 20,
) -> list[RedFlag]:
    """Isolation Forest on transaction features — needs >= 50 rows."""
    if len(df) < 50:
        return []

    work = df.copy()
    vendor_counts = work["vendor"].value_counts()
    work["vendor_freq"] = work["vendor"].map(vendor_counts).astype(float)
    if "date" in work.columns and work["date"].notna().any():
        work["dow"] = work["date"].dt.dayofweek.fillna(-1).astype(float)
        work["month"] = work["date"].dt.month.fillna(-1).astype(float)
    else:
        work["dow"] = -1.0
        work["month"] = -1.0
    if "department" in work.columns:
        dept_codes, _ = pd.factorize(work["department"].astype(str))
        work["dept_code"] = dept_codes.astype(float)
    else:
        work["dept_code"] = 0.0

    features = work[["amount", "vendor_freq", "dow", "month", "dept_code"]].values
    scaled = StandardScaler().fit_transform(features)
    clf = IsolationForest(n_estimators=300, contamination=contamination, random_state=42)
    preds = clf.fit_predict(scaled)
    scores = clf.decision_function(scaled)

    flagged = work[preds == -1].copy()
    flagged["if_score"] = scores[preds == -1]
    flagged = flagged.sort_values("if_score").head(max_flags)

    flags: list[RedFlag] = []
    for idx, row in flagged.iterrows():
        flags.append(
            RedFlag(
                severity="high" if float(row["amount"]) >= 100_000 else "medium",
                category="statistical_anomaly",
                description=(
                    f"{county}: Isolation Forest flagged ${float(row['amount']):,.0f} to "
                    f"'{row['vendor']}' (multivariate outlier)"
                ),
                evidence=_row_provenance(
                    row,
                    extra={"rule": "isolation_forest", "if_score": float(row["if_score"])},
                ),
                recommended_action="Forensic sample — compare to peer transactions same dept/month.",
            )
        )
    return flags


def detect_all_transactions(
    path: str | Path,
    *,
    county: str = "County",
    include_ml: bool = True,
    include_rules: bool = True,
) -> tuple[pd.DataFrame, list[RedFlag]]:
    """Full transaction scan — rules + optional Isolation Forest."""
    df = load_transactions(path)
    flags: list[RedFlag] = []
    if include_rules:
        flags.extend(detect_rule_flags(df, county=county))
    if include_ml:
        flags.extend(detect_isolation_forest(df, county=county))
    return df, flags


def monthly_anomaly_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate for dashboard charts."""
    if "date" not in df.columns or df["date"].isna().all():
        return pd.DataFrame(columns=["month", "total_amount", "tx_count"])
    out = (
        df.assign(month=df["date"].dt.to_period("M").astype(str))
        .groupby("month")
        .agg(total_amount=("amount", "sum"), tx_count=("amount", "count"))
        .reset_index()
        .sort_values("month")
    )
    return out
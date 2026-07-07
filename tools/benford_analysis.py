"""
Benford's Law analysis — first-digit distribution with Nigrini MAD.

Used by procurement_detectors, CLI (scripts/run_benford.py), and inbox CSV audits.
Smoke test only — never a standalone video headline (see audit_strategy.yaml).
"""

from __future__ import annotations

import math
import re
from typing import Any

import numpy as np


def expected_benford_distribution() -> dict[str, float]:
    """P(d) = log10(1 + 1/d) for leading digits 1-9."""
    return {str(d): math.log10(1 + 1 / d) for d in range(1, 10)}


def leading_digit(value: Any) -> str | None:
    """Extract first non-zero digit from a financial amount."""
    clean = re.sub(r"[^0-9.]", "", str(value))
    for char in clean:
        if char in "123456789":
            return char
    return None


def extract_digits(values: list[Any]) -> list[str]:
    return [d for d in (leading_digit(v) for v in values) if d]


def digit_distribution(digits: list[str]) -> dict[str, float]:
    """Observed frequency per digit 1-9."""
    if not digits:
        return {str(d): 0.0 for d in range(1, 10)}
    total = len(digits)
    counts: dict[str, int] = {str(d): 0 for d in range(1, 10)}
    for d in digits:
        counts[d] = counts.get(d, 0) + 1
    return {k: v / total for k, v in counts.items()}


def analyze_digits(
    digits: list[str],
    *,
    abs_threshold: float = 0.04,
) -> dict[str, Any]:
    """
    Full first-digit Benford report with per-digit flags and Nigrini MAD.

    abs_threshold: flag digit when |actual - expected| exceeds this (default 4pp).
    """
    expected = expected_benford_distribution()
    n = len(digits)
    if n == 0:
        return {
            "n": 0,
            "mad": 0.0,
            "verdict": "insufficient_data",
            "suspicious_digit_count": 0,
            "digits": [],
            "warning": "No valid leading digits.",
        }

    actual = digit_distribution(digits)
    rows: list[dict[str, Any]] = []
    suspicious = 0

    for d in range(1, 10):
        key = str(d)
        act = actual.get(key, 0.0)
        exp = expected[key]
        diff = act - exp
        flagged = abs(diff) > abs_threshold
        if flagged:
            suspicious += 1
        rows.append(
            {
                "digit": key,
                "actual_pct": round(act * 100, 2),
                "expected_pct": round(exp * 100, 2),
                "difference_pp": round(diff * 100, 2),
                "flagged": flagged,
            }
        )

    obs = np.array([actual[str(d)] for d in range(1, 10)])
    exp_arr = np.array([expected[str(d)] for d in range(1, 10)])
    mad = float(np.abs(obs - exp_arr).mean())

    if n < 50:
        verdict = "insufficient_data"
    elif mad < 0.006:
        verdict = "close_conformity"
    elif mad < 0.012:
        verdict = "acceptable"
    elif mad < 0.015:
        verdict = "marginal"
    else:
        verdict = "nonconforming"

    warning = None
    if n < 100:
        warning = "Dataset < 100 values — interpret cautiously."

    return {
        "n": n,
        "mad": round(mad, 4),
        "verdict": verdict,
        "suspicious_digit_count": suspicious,
        "digits": rows,
        "warning": warning,
    }


def analyze_amounts(
    amounts: list[float],
    *,
    abs_threshold: float = 0.04,
) -> dict[str, Any]:
    """Analyze a list of numeric amounts."""
    positives = [abs(a) for a in amounts if a is not None and abs(float(a)) >= 1.0]
    digits = extract_digits(positives)
    return analyze_digits(digits, abs_threshold=abs_threshold)


def analyze_csv_column(file_path: str, column_name: str, **kwargs: Any) -> dict[str, Any]:
    """Load CSV column and run Benford analysis."""
    import pandas as pd

    df = pd.read_csv(file_path)
    if column_name not in df.columns:
        raise ValueError(
            f"Column '{column_name}' not found. Available: {', '.join(df.columns)}"
        )
    return analyze_amounts(df[column_name].tolist(), **kwargs)


def format_report(result: dict[str, Any]) -> str:
    """Human-readable table for CLI / logs."""
    lines = [
        "--- BENFORD'S LAW ANALYSIS ---",
        f"n={result['n']}  MAD={result.get('mad')}  verdict={result.get('verdict')}",
        f"{'Digit':<6} | {'Actual %':<10} | {'Expected %':<10} | {'Diff pp':<10} | Status",
        "-" * 55,
    ]
    for row in result.get("digits", []):
        flag = "ANOMALY" if row.get("flagged") else ""
        lines.append(
            f"{row['digit']:<6} | {row['actual_pct']:>7.2f}%   | "
            f"{row['expected_pct']:>7.2f}%   | {row['difference_pp']:>8.2f} | {flag}"
        )
    lines.append("-" * 55)
    sc = result.get("suspicious_digit_count", 0)
    if sc:
        lines.append(f"CONCLUSION: {sc} digit(s) exceed threshold — forensic sample recommended.")
    else:
        lines.append("CONCLUSION: No per-digit threshold breaches.")
    if result.get("warning"):
        lines.append(f"WARNING: {result['warning']}")
    return "\n".join(lines)
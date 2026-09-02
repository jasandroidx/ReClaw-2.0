# Procurement Fraud Audit

A forensic data-engineering pipeline for enterprise procurement payments:
ingest unstructured payment files, run data-quality checks, and surface likely
fraud (duplicate / split vendor payments, threshold gaming) in a defensible,
row-traceable findings report.

Every flag returned carries the **exact contributing row indices**, so every
finding traces back to source data — no number is asserted without evidence.

## Pipeline

```
payments.csv ──► load_payments ──► normalize_vendors ──► detectors ──► findings
                 (type coerce,      (collapse near-       (rolling window,
                  repair log)        duplicate vendors)    Benford, splits...)
```

## Detectors

| Check | What it catches |
|-------|-----------------|
| `rolling_window_flags` | Vendors paid multiple times within a rolling **7-day** window where the sum exceeds a threshold (e.g. R500k). Uses a calendar-time `groupby().rolling('7D')`, not a fixed row count. |
| `split_payment_flags` | Payments clustered just under an approval limit (threshold gaming). |
| `round_number_flags` | Suspiciously round amounts (exact thousands). |
| `benford_first_digit` | First-digit distribution vs Benford's Law; large deviation suggests fabricated amounts. |
| `duplicate_bank_account_flags` | One bank account shared across multiple distinct vendors. |

## The core rolling-window test

```python
work = df.dropna(subset=["payment_date", "amount"]) \
         .sort_values(["vendor_id", "payment_date"]) \
         .set_index("payment_date")
roll = work.groupby("vendor_id")["amount"].rolling("7D")
work["w_sum"] = roll.sum().reset_index(level=0, drop=True)
work["w_cnt"] = roll.count().reset_index(level=0, drop=True)
flagged = work[(work["w_sum"] > 500_000) & (work["w_cnt"] > 1)]
```

SQL equivalent for cross-verification (range-framed window function):

```sql
SUM(amount)  OVER (PARTITION BY vendor_id ORDER BY payment_date
                   RANGE BETWEEN INTERVAL '7 days' PRECEDING AND CURRENT ROW) AS w_sum,
COUNT(*)     OVER (PARTITION BY vendor_id ORDER BY payment_date
                   RANGE BETWEEN INTERVAL '7 days' PRECEDING AND CURRENT ROW) AS w_cnt
-- WHERE w_sum > 500000 AND w_cnt > 1
```

Running both and reconciling the flagged list row-by-row is how results are proven, not asserted.

## Run

```bash
pip install -r requirements.txt
python main.py                       # 100k-row synthetic demo with planted fraud
python main.py payments.csv --threshold 500000 --window 7D --approval-limit 100000
```

Expected columns: `vendor_id, vendor_name, payment_date, amount` (plus optional
`bank_account`, `approver`).

# SF Vendor Payments — Procurement Audit Analytics

Audit analytics project analyzing **$1.87 billion** in vendor payments from the City of San Francisco's FY2020 procurement data. Applied 9 risk-based audit procedures — including Benford's Law analysis — to identify potential duplicate payments, vendor concentration risks, stale encumbrances, and statistical anomalies across 139,664 purchase order records.

**Data source:** [SF Controller's Office — Vendor Payments (Purchase Order Summary)](https://data.sfgov.org/City-Management-and-Ethics/Vendor-Payments-Purchase-Order-Summary-/p5r5-fd7g)

---

## Key Findings

| Finding | Count | Exposure |
|---------|-------|----------|
| Stale encumbrances (>$100K, <20% utilized) | 1,776 POs | $2.14B locked |
| Suspicious round amounts ($10K+ exact multiples) | 645 | $123.9M |
| Potential duplicate payments (cross-PO) | 408 | $4.5M |
| Statistical outliers (>3× IQR) | 6,434 | $1.78B |
| Large credits/reversals (>$10K) | 73 | -$11.6M |
| Sole-source department risk (>50% concentration) | 10 relationships | — |
| Vendor concentration (>1% of total city spend) | 10 vendors | 37.6% of spend |
| **Benford nonconforming departments** | **8 of 15** | — |

---

## Audit Procedures

1. **Vendor Concentration** — Pareto analysis of spend distribution across 5,474 vendors
2. **Duplicate Payments** — Cross-PO matching on vendor + exact amount (threshold: $500)
3. **Round Number Analysis** — Benford's Law-adjacent test for fabricated invoice amounts
4. **Single-Source Risk** — Department-vendor dependency mapping (>50% threshold)
5. **Credit Memo Analysis** — Negative payment patterns indicating disputes or reversals
6. **Outlier Detection** — IQR-based statistical flagging of extreme payment values
7. **Encumbrance Utilization** — Identification of stale purchase orders with locked funds
8. **Spend Category Analysis** — Cross-department comparison of capital and grant spending
9. **Benford's Law** — First-digit, second-digit, and first-two-digit conformity testing at overall, department, and vendor levels using Nigrini's MAD thresholds

---

## Project Structure

```
├── README.md
├── requirements.txt
├── .gitignore
├── scripts/
│   ├── setup_and_slice.py        # Data extraction (1.57M rows → 139K)
│   ├── 02_audit_analysis.py      # 8 audit procedures + flag generation
│   └── 04_benford_analysis.py    # Benford's Law conformity testing
├── sql/
│   └── 03_audit_queries.sql      # SQL equivalents of each test
├── docs/
│   └── SF_Vendor_Payments_Audit_README.docx
└── data/
    ├── raw/                      # .gitignored — download and extract locally
    └── output/                   # Generated CSVs (audit_flags, benford, etc.)
```

---

## How to Reproduce

```bash
# 1. Clone and install
git clone https://github.com/YOUR_USERNAME/sf-vendor-audit.git
cd sf-vendor-audit
pip install -r requirements.txt

# 2. Download the dataset from SF Open Data or Kaggle
#    Place vendor-payments-purchase-order-summary.csv in the project root

# 3. Extract the target fiscal year
python scripts/setup_and_slice.py

# 4. Run audit procedures
python scripts/02_audit_analysis.py

# 5. Run Benford's Law analysis
python scripts/04_benford_analysis.py
```

Output CSVs are saved to `data/output/` and can be imported into Power BI or Tableau.

---

## Tools

| Tool | Usage |
|------|-------|
| **Python** (Pandas, NumPy, SciPy) | Data extraction, statistical analysis, Benford's Law, anomaly detection |
| **SQL** | Audit queries portable across SQLite, PostgreSQL, SQL Server |
| **Power BI / Tableau** | Dashboard (import `vendor_payments_analyzed.csv` from `data/output/`) |

---

## Benford's Law Results

Overall city payments conform closely to Benford's Law (MAD = 0.0051), but department-level testing reveals 8 of 15 departments with nonconforming digit distributions. Public Library (MAD = 0.035) and Fire Department (MAD = 0.023) show the largest deviations. Second-digit analysis shows excess zeros, reinforcing round-number findings.

---

## Data Notes

- FY2020 (July 2019 – June 2020), coinciding with early COVID-19 period
- Public government data — no PII or confidential information
- Full dataset (1.57M rows, FY2007–2020) available at data.sfgov.org

---

**Author:** Osman Abdelmagid  
**Date:** March 2026

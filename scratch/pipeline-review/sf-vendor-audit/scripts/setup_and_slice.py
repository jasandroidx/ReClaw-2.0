"""
SF Vendor Payments - Data Extraction & Sampling
Extracts recent fiscal year data from the full SF Open Data procurement dataset.
Source: https://data.sfgov.org/City-Management-and-Ethics/Vendor-Payments-Purchase-Order-Summary-/p5r5-fd7g

Usage:
    1. Place the full CSV (vendor-payments-purchase-order-summary.csv) in the same
       directory as this script, OR in the parent directory.
    2. Run: python setup_and_slice.py
    3. Output goes to data/raw/vendor_payments_fy2020.csv
"""

import pandas as pd
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

# Look for the source file in common locations
POSSIBLE_PATHS = [
    os.path.join(PROJECT_DIR, '..', 'vendor-payments-purchase-order-summary.csv'),
    os.path.join(PROJECT_DIR, 'vendor-payments-purchase-order-summary.csv'),
    os.path.join(SCRIPT_DIR, 'vendor-payments-purchase-order-summary.csv'),
]

INPUT_FILE = None
for p in POSSIBLE_PATHS:
    if os.path.exists(p):
        INPUT_FILE = p
        break

assert INPUT_FILE, f"Source file not found. Place vendor-payments-purchase-order-summary.csv in the project or parent directory."

OUTPUT_DIR = os.path.join(PROJECT_DIR, 'data', 'raw')
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'vendor_payments_fy2020.csv')

print(f"Loading {os.path.basename(INPUT_FILE)}...")
df = pd.concat([chunk for chunk in pd.read_csv(INPUT_FILE, low_memory=False, chunksize=50000)], ignore_index=True)
print(f"Full dataset: {len(df):,} rows | {df['Fiscal Year'].nunique()} fiscal years")
print(f"Available years: {df['Fiscal Year'].min()} - {df['Fiscal Year'].max()}")

recent = df[df["Fiscal Year"] >= 2020].copy()

if len(recent) > 80000:
    keep = sorted(recent["Fiscal Year"].unique())[-3:]
    recent = recent[recent["Fiscal Year"].isin(keep)]

recent.to_csv(OUTPUT_FILE, index=False)
size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)

print(f"\nExtracted {len(recent):,} rows (FY{recent['Fiscal Year'].min()}-FY{recent['Fiscal Year'].max()})")
print(f"Vendors: {recent['Vendor'].nunique():,} | Departments: {recent['Department Code'].nunique()}")
print(f"Total paid: ${recent['Vouchers Paid'].sum():,.2f}")
print(f"Saved: {OUTPUT_FILE} ({size_mb:.1f} MB)")

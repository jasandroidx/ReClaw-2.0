"""
SF Vendor Payments - Procurement Audit Analytics
Performs risk-based audit procedures on City of San Francisco vendor payment data.
Source: SF Controller's Office via data.sfgov.org (FY2020, 139K+ purchase orders)
"""

import pandas as pd
import numpy as np
from collections import defaultdict

# ── Load & Prepare ──────────────────────────────────────────
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW = os.path.join(BASE_DIR, 'data', 'raw')
DATA_OUT = os.path.join(BASE_DIR, 'data', 'output')
os.makedirs(DATA_OUT, exist_ok=True)

df = pd.read_csv(os.path.join(DATA_RAW, 'vendor_payments_fy2020.csv'), low_memory=False)

# FY2020 data has codes but empty label columns - build lookup
dept_map = {
    'DPH': 'Public Health', 'PUC': 'Public Utilities Commission',
    'MTA': 'Municipal Transportation', 'DPW': 'Public Works',
    'REC': 'Recreation & Parks', 'ADM': 'City Admin/General Services',
    'AIR': 'Airport (SFO)', 'HSA': 'Human Services', 'PRT': 'Port',
    'CHF': "Children, Youth & Families", 'LIB': 'Public Library',
    'POL': 'Police', 'FIR': 'Fire', 'HOM': 'Homelessness',
    'MYR': "Mayor's Office", 'SHF': 'Sheriff', 'ASR': 'Assessor-Recorder',
    'TTX': 'Treasurer/Tax Collector', 'ENV': 'Environment',
    'DAT': 'Disability & Aging', 'JUV': 'Juvenile Probation',
    'TIS': 'Technology/Innovation', 'ART': 'Arts Commission',
    'REG': 'Elections', 'CSC': 'Civil Service Commission',
    'CON': "Controller's Office", 'CPC': 'City Planning',
    'BOS': 'Board of Supervisors', 'CAT': 'City Attorney',
    'DBI': 'Building Inspection', 'HRC': 'Human Rights Commission',
    'HRD': 'Human Resources', 'WAR': 'Public Works (Architectural)',
    'ETH': 'Ethics Commission', 'RNT': 'Rent Board',
    'APD': 'Adult Probation', 'WOM': "Women's Commission",
    'DAA': 'District Attorney', 'PUB': 'Public Defender',
    'BOA': 'Board of Appeals', 'RET': 'Retirement System',
    'ECD': 'Economic & Workforce Dev', 'PHD': 'Public Health - DPH',
}
df['Department'] = df['Department Code'].map(dept_map).fillna(df['Department Code'])

char_map = {
    'NON_PERS_SVCS': 'Non-Personnel Services', 'MTL_SUPP': 'Materials & Supplies',
    'CITY_GR_PROG': 'City Grant Programs', 'AID_ASSIST': 'Aid & Assistance',
    'CAP_OUTLAY': 'Capital Outlay', 'OTH_SUP_CARE_PERS': 'Other Support/Care',
    'DEBT_SERVICE': 'Debt Service', 'PROG_PROJ': 'Program/Project',
}
df['Character'] = df['Character Code'].map(char_map).fillna(df['Character Code'])

print(f"Dataset: {len(df):,} purchase order records | FY{df['Fiscal Year'].iloc[0]}")
print(f"Vendors: {df['Vendor'].nunique():,} | Departments: {df['Department Code'].nunique()}")
print(f"Total Vouchers Paid: ${df['Vouchers Paid'].sum():,.2f}")
print("=" * 70)

results = {}

# ── TEST 1: Vendor Concentration Risk ──────────────────────
# Are a few vendors capturing a disproportionate share of city spend?
print("\n[TEST 1] Vendor Concentration Risk")

vendor_spend = df.groupby('Vendor').agg(
    total_paid=('Vouchers Paid', 'sum'),
    po_count=('Purchase Order', 'nunique'),
    dept_count=('Department Code', 'nunique'),
).sort_values('total_paid', ascending=False)

total_spend = df['Vouchers Paid'].sum()
vendor_spend['pct_of_total'] = vendor_spend['total_paid'] / total_spend

top_10_pct = vendor_spend.head(10)['total_paid'].sum() / total_spend
top_20_pct = vendor_spend.head(20)['total_paid'].sum() / total_spend

print(f"  Top 10 vendors control {top_10_pct:.1%} of total spend")
print(f"  Top 20 vendors control {top_20_pct:.1%} of total spend")

# Flag vendors with >1% of total city spend
conc_threshold = 0.01
high_conc = vendor_spend[vendor_spend['pct_of_total'] > conc_threshold]
print(f"  {len(high_conc)} vendors exceed {conc_threshold:.0%} of total spend")

results['vendor_concentration'] = high_conc.reset_index()


# ── TEST 2: Duplicate Payment Detection ────────────────────
# Same vendor + same exact amount across DIFFERENT purchase orders (>$500)
print("\n[TEST 2] Duplicate Payment Detection")

paid_only = df[df['Vouchers Paid'] > 500].copy()
dup_check = paid_only.groupby(['Vendor', 'Vouchers Paid']).agg(
    po_count=('Purchase Order', 'nunique'),
    po_list=('Purchase Order', lambda x: list(x.unique()))
).reset_index()
dups = dup_check[dup_check['po_count'] > 1]

dup_txns = paid_only.merge(dups[['Vendor', 'Vouchers Paid']], on=['Vendor', 'Vouchers Paid'])
dup_exposure = dups['Vouchers Paid'].mul(dups['po_count'] - 1).sum()

print(f"  {len(dups)} potential duplicate payment patterns found")
print(f"  Involving {dup_txns['Vendor'].nunique()} vendors")
print(f"  Estimated overpayment exposure: ${dup_exposure:,.2f}")

results['duplicates'] = dup_txns


# ── TEST 3: Round Number Analysis ──────────────────────────
# Exact round amounts may indicate estimated/fabricated invoices
print("\n[TEST 3] Round Number Analysis")

paid_positive = df[df['Vouchers Paid'] > 0].copy()
paid_positive['is_round_1k'] = (paid_positive['Vouchers Paid'] % 1000 == 0)
paid_positive['is_round_10k'] = (paid_positive['Vouchers Paid'] % 10000 == 0)

round_1k = paid_positive[paid_positive['is_round_1k'] & (paid_positive['Vouchers Paid'] >= 1000)]
round_10k = paid_positive[paid_positive['is_round_10k'] & (paid_positive['Vouchers Paid'] >= 10000)]

expected_pct = 0.001  # statistically, <0.1% of natural payments are exact multiples
actual_pct = len(round_1k) / len(paid_positive)

print(f"  Payments that are exact $1K multiples: {len(round_1k)} ({actual_pct:.2%} of paid vouchers)")
print(f"  Payments that are exact $10K multiples: {len(round_10k)}")
print(f"  Total round-number exposure: ${round_1k['Vouchers Paid'].sum():,.2f}")

results['round_numbers'] = round_1k


# ── TEST 4: Single-Source / Sole-Vendor Department Risk ────
# Departments relying heavily on a single vendor
print("\n[TEST 4] Single-Source Department Risk")

dept_vendor = df[df['Vouchers Paid'] > 0].groupby(['Department Code', 'Department', 'Vendor']).agg(
    total_paid=('Vouchers Paid', 'sum'),
    po_count=('Purchase Order', 'nunique')
).reset_index()

dept_total = df[df['Vouchers Paid'] > 0].groupby('Department Code')['Vouchers Paid'].sum().reset_index()
dept_total.columns = ['Department Code', 'dept_total_paid']

dept_vendor = dept_vendor.merge(dept_total, on='Department Code')
dept_vendor['vendor_pct_of_dept'] = dept_vendor['total_paid'] / dept_vendor['dept_total_paid']

# Flag: vendor captures >50% of a department's spend AND >$100K
sole_source = dept_vendor[
    (dept_vendor['vendor_pct_of_dept'] > 0.50) &
    (dept_vendor['total_paid'] > 100_000)
].sort_values('total_paid', ascending=False)

print(f"  {len(sole_source)} vendor-department relationships with >50% spend concentration")
for _, row in sole_source.head(5).iterrows():
    print(f"    {row['Vendor'][:40]:40s} → {row['Department']:25s} {row['vendor_pct_of_dept']:.0%} (${row['total_paid']:,.0f})")

results['sole_source'] = sole_source


# ── TEST 5: Negative Payments / Credit Memo Analysis ───────
# Credits and reversals may indicate returns, disputes, or adjustments
print("\n[TEST 5] Negative Payments / Credit Memo Analysis")

negatives = df[df['Vouchers Paid'] < 0].copy()
neg_by_vendor = negatives.groupby('Vendor').agg(
    credit_count=('Vouchers Paid', 'count'),
    total_credits=('Vouchers Paid', 'sum')
).sort_values('total_credits')

print(f"  {len(negatives)} negative payment records (credits/reversals)")
print(f"  Total credits: ${negatives['Vouchers Paid'].sum():,.2f}")
print(f"  Vendors with credits: {negatives['Vendor'].nunique()}")
print(f"  Largest single credit: ${negatives['Vouchers Paid'].min():,.2f}")

results['negatives'] = negatives


# ── TEST 6: High-Value Outlier Detection ───────────────────
# Statistical outliers using IQR method
print("\n[TEST 6] High-Value Outlier Detection")

paid_nonzero = df[df['Vouchers Paid'] > 0]['Vouchers Paid']
Q1 = paid_nonzero.quantile(0.25)
Q3 = paid_nonzero.quantile(0.75)
IQR = Q3 - Q1
upper_fence = Q3 + 3 * IQR  # extreme outliers (3x IQR)

outliers = df[df['Vouchers Paid'] > upper_fence].copy()
print(f"  IQR: ${IQR:,.2f} | Upper fence (3x IQR): ${upper_fence:,.2f}")
print(f"  {len(outliers)} extreme outlier payments above ${upper_fence:,.0f}")
print(f"  Total outlier exposure: ${outliers['Vouchers Paid'].sum():,.2f}")

results['outliers'] = outliers


# ── TEST 7: Encumbrance vs Payment Gap Analysis ────────────
# Large remaining encumbrances may indicate stale POs or budget parking
print("\n[TEST 7] Encumbrance Utilization Analysis")

po_summary = df.groupby(['Purchase Order', 'Vendor']).agg(
    total_paid=('Vouchers Paid', 'sum'),
    total_pending=('Vouchers Pending', 'sum'),
    total_encumbrance=('Encumbrance Balance', 'sum'),
).reset_index()

po_summary['total_committed'] = po_summary['total_paid'] + po_summary['total_pending'] + po_summary['total_encumbrance']
po_summary['utilization'] = np.where(
    po_summary['total_committed'] > 0,
    po_summary['total_paid'] / po_summary['total_committed'],
    0
)

# Flag POs with large unused encumbrances (>$100K remaining, <20% utilized)
stale_pos = po_summary[
    (po_summary['total_encumbrance'] > 100_000) &
    (po_summary['utilization'] < 0.20)
].sort_values('total_encumbrance', ascending=False)

print(f"  {len(stale_pos)} POs with >$100K encumbrance and <20% utilization")
print(f"  Total locked funds: ${stale_pos['total_encumbrance'].sum():,.2f}")

results['stale_encumbrances'] = stale_pos


# ── TEST 8: Spend Category Anomalies ──────────────────────
# Unusual spend patterns by category and department
print("\n[TEST 8] Cross-Department Spend Pattern Analysis")

dept_char = df[df['Vouchers Paid'] > 0].groupby(['Department', 'Character']).agg(
    total_paid=('Vouchers Paid', 'sum'),
    txn_count=('Vouchers Paid', 'count')
).reset_index()

# Flag: Capital Outlay or Grant Programs with unusual patterns
capital = df[(df['Character Code'] == 'CAP_OUTLAY') & (df['Vouchers Paid'] > 0)]
grants = df[(df['Character Code'] == 'CITY_GR_PROG') & (df['Vouchers Paid'] > 0)]

print(f"  Capital Outlay: {len(capital)} records, ${capital['Vouchers Paid'].sum():,.2f}")
print(f"  City Grant Programs: {len(grants)} records, ${grants['Vouchers Paid'].sum():,.2f}")

results['dept_spend_patterns'] = dept_char

# ══════════════════════════════════════════════════════════════
# COMPILE & EXPORT
# ══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("AUDIT SUMMARY")
print("=" * 70)

# Build master flag table
flags = []

for _, row in results['vendor_concentration'].iterrows():
    flags.append({'Vendor': row['Vendor'], 'Flag': 'Vendor Concentration', 'Risk': 'Medium',
                  'Detail': f"{row['pct_of_total']:.1%} of total city spend", 'Amount': row['total_paid']})

for _, row in results['duplicates'].drop_duplicates(['Vendor', 'Vouchers Paid']).iterrows():
    flags.append({'Vendor': row['Vendor'], 'Flag': 'Potential Duplicate', 'Risk': 'High',
                  'Detail': f"${row['Vouchers Paid']:,.2f} paid across multiple POs", 'Amount': row['Vouchers Paid']})

for _, row in results['round_numbers'].iterrows():
    if row['Vouchers Paid'] >= 10000:
        flags.append({'Vendor': row['Vendor'], 'Flag': 'Suspicious Round Amount', 'Risk': 'Medium',
                      'Detail': f"Exact ${row['Vouchers Paid']:,.0f}", 'Amount': row['Vouchers Paid']})

for _, row in results['sole_source'].iterrows():
    flags.append({'Vendor': row['Vendor'], 'Flag': 'Sole-Source Risk', 'Risk': 'High',
                  'Detail': f"{row['vendor_pct_of_dept']:.0%} of {row['Department']} spend", 'Amount': row['total_paid']})

for _, row in results['negatives'].iterrows():
    if row['Vouchers Paid'] < -10000:
        flags.append({'Vendor': row['Vendor'], 'Flag': 'Large Credit/Reversal', 'Risk': 'Medium',
                      'Detail': f"Credit of ${row['Vouchers Paid']:,.2f}", 'Amount': row['Vouchers Paid']})

for _, row in results['outliers'].head(100).iterrows():
    flags.append({'Vendor': row['Vendor'], 'Flag': 'Statistical Outlier', 'Risk': 'High',
                  'Detail': f"Payment ${row['Vouchers Paid']:,.2f} exceeds 3x IQR", 'Amount': row['Vouchers Paid']})

for _, row in results['stale_encumbrances'].iterrows():
    flags.append({'Vendor': row['Vendor'], 'Flag': 'Stale Encumbrance', 'Risk': 'Medium',
                  'Detail': f"${row['total_encumbrance']:,.0f} uncommitted, {row['utilization']:.0%} utilized",
                  'Amount': row['total_encumbrance']})

flag_df = pd.DataFrame(flags)
flag_summary = flag_df['Flag'].value_counts()
risk_summary = flag_df['Risk'].value_counts()

print(f"\nTotal flagged items: {len(flag_df)}")
print(f"\nBy flag type:")
for f, c in flag_summary.items():
    print(f"  {f}: {c}")
print(f"\nBy risk level:")
for r, c in risk_summary.items():
    print(f"  {r}: {c}")

# Export
flag_df.to_csv(os.path.join(DATA_OUT, 'audit_flags.csv'), index=False)

# Full dataset with flag indicator for Power BI
df['Is_Flagged'] = df['Vendor'].isin(flag_df['Vendor'].unique()).astype(int)
df.to_csv(os.path.join(DATA_OUT, 'vendor_payments_analyzed.csv'), index=False)

# Vendor risk profile
vendor_flags = flag_df.groupby('Vendor').agg(
    flag_count=('Flag', 'count'),
    flag_types=('Flag', lambda x: ' | '.join(sorted(set(x)))),
    max_risk=('Risk', lambda x: 'High' if 'High' in x.values else 'Medium'),
    total_flagged_amount=('Amount', 'sum')
).sort_values('total_flagged_amount', ascending=False).reset_index()
vendor_flags.to_csv(os.path.join(DATA_OUT, 'vendor_risk_profile.csv'), index=False)

# Department spend summary
dept_summary = df[df['Vouchers Paid'] > 0].groupby(['Department Code', 'Department']).agg(
    total_paid=('Vouchers Paid', 'sum'),
    vendor_count=('Vendor', 'nunique'),
    po_count=('Purchase Order', 'nunique'),
    avg_payment=('Vouchers Paid', 'mean'),
    max_payment=('Vouchers Paid', 'max'),
).sort_values('total_paid', ascending=False).reset_index()
dept_summary.to_csv(os.path.join(DATA_OUT, 'department_summary.csv'), index=False)

print(f"\nFiles saved to {DATA_OUT}:")
print(f"  audit_flags.csv              ({len(flag_df)} flags)")
print(f"  vendor_risk_profile.csv      ({len(vendor_flags)} vendors flagged)")
print(f"  vendor_payments_analyzed.csv  ({len(df)} rows)")
print(f"  department_summary.csv       ({len(dept_summary)} departments)")

# ══════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

CHARTS_DIR = os.path.join(DATA_OUT, 'charts')
os.makedirs(CHARTS_DIR, exist_ok=True)

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'figure.dpi': 150,
})

NAVY = '#1B3A5C'
ACCENT = '#2E75B6'
CORAL = '#E8593C'
GRAY = '#888888'
LIGHT = '#EDF3F8'

# 1. Flags by type
fig, ax = plt.subplots(figsize=(10, 5))
flag_counts = flag_df['Flag'].value_counts()
bars = ax.barh(flag_counts.index[::-1], flag_counts.values[::-1], color=ACCENT, edgecolor='white')
ax.set_xlabel('Count')
ax.set_title('Audit Flags by Type', fontsize=14, fontweight='bold', color=NAVY, pad=15)
for bar, val in zip(bars, flag_counts.values[::-1]):
    ax.text(bar.get_width() + 15, bar.get_y() + bar.get_height()/2, f'{val:,}',
            va='center', fontsize=10, color=NAVY)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '01_flags_by_type.png'), bbox_inches='tight')
plt.close()

# 2. Top 10 vendors by spend
fig, ax = plt.subplots(figsize=(10, 5))
top10 = vendor_spend.head(10).sort_values('total_paid')
bars = ax.barh(top10.index, top10['total_paid'] / 1e6, color=ACCENT, edgecolor='white')
ax.set_xlabel('Total Paid ($M)')
ax.set_title('Top 10 Vendors by Spend', fontsize=14, fontweight='bold', color=NAVY, pad=15)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}M'))
for bar, val in zip(bars, top10['total_paid']):
    ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, f'${val/1e6:,.1f}M',
            va='center', fontsize=9, color=NAVY)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '02_top_vendors.png'), bbox_inches='tight')
plt.close()

# 3. Department spend distribution
fig, ax = plt.subplots(figsize=(10, 6))
top_depts = dept_summary.head(12).sort_values('total_paid')
bars = ax.barh(top_depts['Department Code'], top_depts['total_paid'] / 1e6, color=ACCENT, edgecolor='white')
ax.set_xlabel('Total Paid ($M)')
ax.set_title('Spend by Department (Top 12)', fontsize=14, fontweight='bold', color=NAVY, pad=15)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}M'))
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '03_dept_spend.png'), bbox_inches='tight')
plt.close()

# 4. Risk level breakdown (pie)
fig, ax = plt.subplots(figsize=(6, 6))
risk_data = flag_df['Risk'].value_counts()
colors = [CORAL, ACCENT]
wedges, texts, autotexts = ax.pie(risk_data.values, labels=risk_data.index, autopct='%1.0f%%',
                                   colors=colors, startangle=90, textprops={'fontsize': 12})
for t in autotexts:
    t.set_color('white')
    t.set_fontweight('bold')
ax.set_title('Flags by Risk Level', fontsize=14, fontweight='bold', color=NAVY, pad=15)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '04_risk_breakdown.png'), bbox_inches='tight')
plt.close()

# 5. Payment distribution - two panels: full view + zoomed to threshold
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={'width_ratios': [1, 1]})

paid_pos = df[df['Vouchers Paid'] > 0]['Vouchers Paid']

# Left panel: zoomed view showing threshold
zoomed = paid_pos[paid_pos <= 100000]
ax1.hist(zoomed, bins=80, color=ACCENT, edgecolor='white', alpha=0.85)
ax1.axvline(x=16608, color=CORAL, linestyle='--', linewidth=2, label='Outlier threshold ($16,608)')
ax1.set_xlabel('Payment Amount ($)')
ax1.set_ylabel('Frequency')
ax1.set_title('Payments up to $100K', fontsize=13, fontweight='bold', color=NAVY, pad=12)
ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x/1000:.0f}K'))
ax1.legend(frameon=False, fontsize=9)

# Right panel: log-log full distribution
bins_log = np.logspace(np.log10(1), np.log10(paid_pos.max()), 60)
ax2.hist(paid_pos, bins=bins_log, color=ACCENT, edgecolor='white', alpha=0.85)
ax2.set_xscale('log')
ax2.set_yscale('log')
ax2.axvline(x=16608, color=CORAL, linestyle='--', linewidth=2, label='Outlier threshold ($16,608)')
ax2.set_xlabel('Payment Amount ($, log scale)')
ax2.set_ylabel('Frequency (log scale)')
ax2.set_title('Full Distribution (log-log)', fontsize=13, fontweight='bold', color=NAVY, pad=12)
ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}' if x < 1000 else f'${x/1000:,.0f}K' if x < 1e6 else f'${x/1e6:,.0f}M'))
ax2.legend(frameon=False, fontsize=9)

fig.suptitle('Payment Amount Distribution', fontsize=15, fontweight='bold', color=NAVY, y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '05_payment_distribution.png'), bbox_inches='tight')
plt.close()

print(f"\nCharts saved to {CHARTS_DIR}/")

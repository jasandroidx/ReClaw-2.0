"""
SF Vendor Payments - Benford's Law Analysis
Tests conformity of payment amounts to the expected Benford distribution.
Non-conforming departments or vendors may warrant additional audit scrutiny.

Reference: Nigrini, M. (2012). Benford's Law. Wiley.
MAD thresholds per Nigrini: <0.006 Close, <0.012 Acceptable, <0.015 Marginal, >=0.015 Nonconforming
"""

import pandas as pd
import numpy as np
from scipy import stats
import json

# ── Helpers ─────────────────────────────────────────────────

def get_digit(x, position=1):
    """Extract the nth significant digit from a number."""
    s = f"{x:.2f}".lstrip('0').lstrip('.')
    digits = ''.join(c for c in s if c.isdigit()).lstrip('0')
    if position == 1:
        return int(digits[0]) if digits else 0
    elif position == 2:
        return int(digits[1]) if len(digits) >= 2 else -1
    elif position == 12:
        return int(digits[:2]) if len(digits) >= 2 else -1
    return 0

def benford_expected(position=1):
    """Return expected Benford distribution for first or second digit."""
    if position == 1:
        return pd.Series({d: np.log10(1 + 1/d) for d in range(1, 10)})
    elif position == 2:
        return pd.Series({d: sum(np.log10(1 + 1/(10*d1 + d)) for d1 in range(1, 10)) for d in range(0, 10)})
    elif position == 12:
        return pd.Series({d: np.log10(1 + 1/d) for d in range(10, 100)})

def benford_test(values, position=1):
    """Run Benford test on a series of positive numbers. Returns dict with results."""
    digits = values.apply(lambda x: get_digit(x, position))
    
    if position == 1:
        digits = digits[digits > 0]
        digit_range = range(1, 10)
    elif position == 2:
        digits = digits[digits >= 0]
        digit_range = range(0, 10)
    elif position == 12:
        digits = digits[digits >= 10]
        digit_range = range(10, 100)
    
    if len(digits) < 50:
        return None
    
    expected = benford_expected(position)
    obs_counts = digits.value_counts()
    for d in digit_range:
        if d not in obs_counts.index:
            obs_counts[d] = 0
    obs_counts = obs_counts[list(digit_range)].sort_index()
    obs_pct = obs_counts / obs_counts.sum()
    exp_counts = pd.Series({d: expected[d] * len(digits) for d in digit_range})
    
    mad = sum(abs(obs_pct.get(d, 0) - expected[d]) for d in digit_range) / len(digit_range)
    chi2, p = stats.chisquare(obs_counts, exp_counts)
    
    if mad < 0.006: conformity = "Close"
    elif mad < 0.012: conformity = "Acceptable"
    elif mad < 0.015: conformity = "Marginal"
    else: conformity = "Nonconforming"
    
    return {
        'n': len(digits),
        'mad': round(mad, 4),
        'chi2': round(chi2, 2),
        'p_value': p,
        'conformity': conformity,
        'observed': obs_pct.to_dict(),
        'expected': expected.to_dict(),
    }


# ── Load Data ──────────────────────────────────────────────

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW = os.path.join(BASE_DIR, 'data', 'raw')
DATA_OUT = os.path.join(BASE_DIR, 'data', 'output')
os.makedirs(DATA_OUT, exist_ok=True)

df = pd.read_csv(os.path.join(DATA_RAW, 'vendor_payments_fy2020.csv'), low_memory=False)
paid = df[df['Vouchers Paid'] > 0]['Vouchers Paid']

dept_map = {
    'DPH': 'Public Health', 'PUC': 'Public Utilities', 'MTA': 'Municipal Transportation',
    'DPW': 'Public Works', 'REC': 'Recreation & Parks', 'ADM': 'City Admin',
    'AIR': 'Airport (SFO)', 'HSA': 'Human Services', 'PRT': 'Port',
    'CHF': 'Children/Youth/Families', 'LIB': 'Public Library', 'POL': 'Police',
    'FIR': 'Fire', 'HOM': 'Homelessness', 'MYR': "Mayor's Office",
}


# ── Test 1: Overall First Digit ────────────────────────────

print("=" * 70)
print("BENFORD'S LAW ANALYSIS — SF Vendor Payments FY2020")
print("=" * 70)

result_1d = benford_test(paid, position=1)

print(f"\n[FIRST DIGIT TEST] n={result_1d['n']:,}")
print(f"{'Digit':>5} {'Expected':>10} {'Observed':>10} {'Deviation':>10}")
for d in range(1, 10):
    exp = result_1d['expected'][d]
    obs = result_1d['observed'].get(d, 0)
    print(f"{d:>5} {exp:>10.4f} {obs:>10.4f} {obs-exp:>+10.4f}")

print(f"\nMAD: {result_1d['mad']:.4f} → {result_1d['conformity']}")
print(f"Chi-square: {result_1d['chi2']:.2f} (p={result_1d['p_value']:.2e})")


# ── Test 2: Second Digit ──────────────────────────────────

result_2d = benford_test(paid, position=2)

print(f"\n[SECOND DIGIT TEST] n={result_2d['n']:,}")
print(f"{'Digit':>5} {'Expected':>10} {'Observed':>10} {'Deviation':>10}")
for d in range(0, 10):
    exp = result_2d['expected'][d]
    obs = result_2d['observed'].get(d, 0)
    flag = " ←" if abs(obs - exp) > 0.012 else ""
    print(f"{d:>5} {exp:>10.4f} {obs:>10.4f} {obs-exp:>+10.4f}{flag}")

print(f"\nMAD: {result_2d['mad']:.4f} → {result_2d['conformity']}")


# ── Test 3: First-Two Digits Anomalies ─────────────────────

result_f2 = benford_test(paid, position=12)
exp_f2 = benford_expected(12)
obs_f2 = result_f2['observed']

deviations = {d: obs_f2.get(d, 0) - exp_f2[d] for d in range(10, 100) if d in obs_f2}
top_anomalies = sorted(deviations.items(), key=lambda x: abs(x[1]), reverse=True)[:10]

print(f"\n[FIRST-TWO DIGITS] Top 10 anomalous digit pairs:")
print(f"{'Pair':>5} {'Expected':>10} {'Observed':>10} {'Deviation':>10}")
for d, diff in top_anomalies:
    print(f"{d:>5} {exp_f2[d]:>10.4f} {obs_f2.get(d,0):>10.4f} {diff:>+10.4f}")


# ── Test 4: Department-Level Conformity ────────────────────

print(f"\n{'='*70}")
print("DEPARTMENT-LEVEL BENFORD CONFORMITY")
print(f"{'='*70}")
print(f"{'Department':<30} {'n':>7} {'MAD':>8} {'Chi2':>8} {'Conformity':<15}")
print("-" * 70)

dept_results = []
for dept in df['Department Code'].value_counts().head(15).index:
    dept_paid = df[(df['Department Code'] == dept) & (df['Vouchers Paid'] > 0)]['Vouchers Paid']
    result = benford_test(dept_paid, position=1)
    if result is None:
        continue
    
    name = dept_map.get(dept, dept)
    label = f"{dept} ({name})"
    marker = " ← INVESTIGATE" if result['conformity'] == 'Nonconforming' else ""
    print(f"{label:<30} {result['n']:>7,} {result['mad']:>8.4f} {result['chi2']:>8.1f} {result['conformity']:<15}{marker}")
    
    dept_results.append({
        'Department Code': dept,
        'Department': name,
        'n': result['n'],
        'MAD': result['mad'],
        'Chi2': result['chi2'],
        'p_value': result['p_value'],
        'Conformity': result['conformity'],
    })


# ── Test 5: Vendor-Level (High-Spend Vendors) ─────────────

print(f"\n{'='*70}")
print("VENDOR-LEVEL BENFORD CONFORMITY (Top 30 by spend)")
print(f"{'='*70}")

top_vendors = df[df['Vouchers Paid'] > 0].groupby('Vendor')['Vouchers Paid'].agg(['sum', 'count']).sort_values('sum', ascending=False).head(30)

vendor_results = []
for vendor in top_vendors.index:
    v_paid = df[(df['Vendor'] == vendor) & (df['Vouchers Paid'] > 0)]['Vouchers Paid']
    result = benford_test(v_paid, position=1)
    if result is None:
        continue
    
    marker = " ← INVESTIGATE" if result['conformity'] == 'Nonconforming' else ""
    if result['n'] >= 50:
        print(f"  {vendor[:45]:<45} n={result['n']:>5} MAD={result['mad']:.4f} {result['conformity']}{marker}")
    
    vendor_results.append({
        'Vendor': vendor,
        'n': result['n'],
        'Total_Paid': top_vendors.loc[vendor, 'sum'],
        'MAD': result['mad'],
        'Conformity': result['conformity'],
    })


# ── Export ─────────────────────────────────────────────────

print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")

nonconforming_depts = [r for r in dept_results if r['Conformity'] == 'Nonconforming']
nonconforming_vendors = [r for r in vendor_results if r['Conformity'] == 'Nonconforming']

print(f"\nOverall conformity: {result_1d['conformity']} (MAD={result_1d['mad']:.4f})")
print(f"Departments tested: {len(dept_results)} | Nonconforming: {len(nonconforming_depts)}")
print(f"Vendors tested: {len(vendor_results)} | Nonconforming: {len(nonconforming_vendors)}")

print("\nDepartments requiring further investigation:")
for r in nonconforming_depts:
    print(f"  {r['Department Code']} ({r['Department']}): MAD={r['MAD']:.4f}, n={r['n']:,}")

# Save results
pd.DataFrame(dept_results).to_csv(os.path.join(DATA_OUT, 'benford_departments.csv'), index=False)
pd.DataFrame(vendor_results).to_csv(os.path.join(DATA_OUT, 'benford_vendors.csv'), index=False)

# Save first-digit distribution for charting
dist_df = pd.DataFrame({
    'Digit': range(1, 10),
    'Expected': [benford_expected(1)[d] for d in range(1, 10)],
    'Observed': [result_1d['observed'].get(d, 0) for d in range(1, 10)],
})
dist_df['Deviation'] = dist_df['Observed'] - dist_df['Expected']
dist_df.to_csv(os.path.join(DATA_OUT, 'benford_first_digit_distribution.csv'), index=False)

print(f"\nFiles saved to {DATA_OUT}:")
print(f"  benford_departments.csv")
print(f"  benford_vendors.csv")
print(f"  benford_first_digit_distribution.csv")

# ══════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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
GREEN = '#2D8C4E'

# 6. First digit: expected vs observed
fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(1, 10)
width = 0.35
ax.bar(x - width/2, dist_df['Expected'], width, label='Benford Expected', color=ACCENT, edgecolor='white')
ax.bar(x + width/2, dist_df['Observed'], width, label='SF Payments Observed', color=CORAL, edgecolor='white')
ax.set_xlabel('First Digit')
ax.set_ylabel('Proportion')
ax.set_title(f'Benford\'s Law: First Digit Distribution (MAD={result_1d["mad"]:.4f})',
             fontsize=14, fontweight='bold', color=NAVY, pad=15)
ax.set_xticks(x)
ax.legend(frameon=False)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '06_benford_first_digit.png'), bbox_inches='tight')
plt.close()

# 7. Second digit: expected vs observed
fig, ax = plt.subplots(figsize=(10, 5))
x2 = np.arange(0, 10)
obs_2 = [result_2d['observed'].get(d, 0) for d in range(0, 10)]
exp_2 = [benford_expected(2)[d] for d in range(0, 10)]
ax.bar(x2 - width/2, exp_2, width, label='Benford Expected', color=ACCENT, edgecolor='white')
ax.bar(x2 + width/2, obs_2, width, label='SF Payments Observed', color=CORAL, edgecolor='white')
ax.set_xlabel('Second Digit')
ax.set_ylabel('Proportion')
ax.set_title('Second Digit Distribution', fontsize=14, fontweight='bold', color=NAVY, pad=15)
ax.set_xticks(x2)
ax.annotate('Excess zeros\n(round numbers)', xy=(0.2, obs_2[0]), xytext=(4, obs_2[0] - 0.01),
            arrowprops=dict(arrowstyle='->', color=NAVY, lw=1.5), fontsize=10, color=NAVY)
ax.legend(frameon=False)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '07_benford_second_digit.png'), bbox_inches='tight')
plt.close()

# 8. Department MAD scores
fig, ax = plt.subplots(figsize=(10, 6))
dept_df = pd.DataFrame(dept_results).sort_values('MAD')
colors = [CORAL if c == 'Nonconforming' else ACCENT if c in ['Close', 'Acceptable'] else '#F5A623'
          for c in dept_df['Conformity']]
bars = ax.barh(dept_df['Department Code'], dept_df['MAD'], color=colors, edgecolor='white')
ax.axvline(x=0.006, color=GREEN, linestyle='--', linewidth=1, alpha=0.7, label='Close (<0.006)')
ax.axvline(x=0.012, color='#F5A623', linestyle='--', linewidth=1, alpha=0.7, label='Acceptable (<0.012)')
ax.axvline(x=0.015, color=CORAL, linestyle='--', linewidth=1, alpha=0.7, label='Nonconforming (≥0.015)')
ax.set_xlabel('Mean Absolute Deviation (MAD)')
ax.set_title('Benford Conformity by Department', fontsize=14, fontweight='bold', color=NAVY, pad=15)
ax.legend(frameon=False, fontsize=9, loc='lower right')
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '08_benford_dept_conformity.png'), bbox_inches='tight')
plt.close()

# 9. First-two digits deviation (spike chart)
fig, ax = plt.subplots(figsize=(14, 5))
digits_range = range(10, 100)
obs_f2_vals = [obs_f2.get(d, 0) for d in digits_range]
exp_f2_vals = [exp_f2[d] for d in digits_range]
dev_vals = [obs_f2.get(d, 0) - exp_f2[d] for d in digits_range]
colors_dev = [CORAL if d > 0.001 else ACCENT if d < -0.001 else NAVY for d in dev_vals]
ax.bar(list(digits_range), dev_vals, color=colors_dev, width=0.8)
ax.axhline(y=0, color=NAVY, linewidth=0.5)
ax.set_xlabel('First Two Digits')
ax.set_ylabel('Deviation from Benford')
ax.set_title('First-Two Digit Deviations from Expected Benford Distribution',
             fontsize=13, fontweight='bold', color=NAVY, pad=15)

top_devs = sorted(zip(digits_range, dev_vals), key=lambda x: abs(x[1]), reverse=True)[:3]
for d, v in top_devs:
    offset = 0.0015 if v > 0 else -0.0015
    ax.annotate(f'{d}', xy=(d, v), xytext=(d + 3, v + offset),
                arrowprops=dict(arrowstyle='->', color=NAVY, lw=1),
                fontsize=10, ha='center', color=NAVY, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, '09_benford_first_two_digits.png'), bbox_inches='tight')
plt.close()

print(f"Charts saved to {CHARTS_DIR}/")

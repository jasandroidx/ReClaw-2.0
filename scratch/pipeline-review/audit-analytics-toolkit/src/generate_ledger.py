"""Generate a synthetic general ledger with planted control exceptions.

Produces (all seeded, fully reproducible):

    data/journal_entries.csv   ~36,000 AP/GL lines for FY2025
    data/users.csv             user master with posting/approval rights
    data/ground_truth.csv      entry_id -> planted anomaly type (for evaluation)

The baseline population is designed to be "clean": log-normal amounts
(naturally Benford-conformant), business-hours weekday posting times, and
valid poster/approver pairs. Six classes of exceptions are then planted so
the detectors in audit_tests.py can be evaluated against known ground truth.

Usage:
    python src/generate_ledger.py
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

SEED = 42
N_BASELINE = 35_000
FY_START = datetime(2025, 1, 1)
APPROVAL_THRESHOLD_RM = 50_000.0

VENDOR_NAMES = [
    "Maju Jaya Trading Sdn Bhd", "Sinar Harapan Enterprise", "TechNova Solutions Sdn Bhd",
    "Puncak Emas Logistics Sdn Bhd", "Delima Fresh Supplies", "KL Metro Services Sdn Bhd",
    "Borneo Timber Industries", "Selangor Steel Works Sdn Bhd", "Nusantara IT Distribution",
    "Harmoni Facilities Management", "Cahaya Elektrik Sdn Bhd", "Penang Precision Parts",
    "Bintang Utara Transport", "Melaka Packaging Industries", "Seri Wangi Catering Sdn Bhd",
    "Johor Chemical Supplies", "Amanah Office Solutions", "Gemilang Printing Press",
    "Ipoh Engineering Works Sdn Bhd", "Damai Security Services", "Kenanga Stationery Supplies",
    "Perdana Auto Fleet Sdn Bhd", "Sungai Besi Hardware", "Wawasan Training Consultants",
    "Bukit Bintang Media Group", "Klang Valley Couriers", "Mutiara Cleaning Services",
    "Sabah Marine Supplies Sdn Bhd", "Temasek Instruments", "Angkasa Telecommunication",
    "Rimba Landscaping Sdn Bhd", "Kota Kinabalu Freight", "Seremban Tools & Dies",
    "Lestari Environmental Services", "Merdeka Uniform Supplies", "Cyberjaya Data Systems",
    "Putra Heights Construction", "Taman Desa Food Industries", "Kuantan Port Services",
    "Alor Setar Agri Supplies", "Genting View Hospitality", "Subang Aviation Parts",
    "Bangsar Interior Design", "Petaling Jaya Motors", "Shah Alam Plastics Sdn Bhd",
    "Titiwangsa Medical Supplies", "Langkawi Duty Services", "Kelantan Textiles Sdn Bhd",
    "Ampang Glass & Aluminium", "Cheras Building Materials", "Kepong Cold Storage",
    "Bandar Utama Events Sdn Bhd", "Setapak Scaffolding", "Puchong Electronics Hub",
    "Rawang Cement Distributors", "Nilai Furniture Gallery", "Kajang Satay House Catering",
    "Skudai Lab Equipment", "Tawau Palm Logistics", "Miri Offshore Supplies",
]

FIRST_NAMES = [
    "Aisyah", "Farid", "Mei Ling", "Rajesh", "Nurul", "Wei Jian", "Siti", "Arun",
    "Hafiz", "Li Wen", "Zainab", "Kumar", "Amirul", "Xin Yi", "Fatimah", "Ganesh",
    "Danial", "Hui Min", "Balqis", "Vijay", "Irfan", "Shu Fen", "Melati", "Suresh",
]

ACCOUNTS = [
    ("5100", "Cost of goods sold"), ("5200", "Freight & logistics"),
    ("6100", "Office supplies"), ("6200", "IT & software"),
    ("6300", "Professional fees"), ("6400", "Repairs & maintenance"),
    ("6500", "Utilities"), ("6600", "Marketing"), ("6700", "Travel & entertainment"),
]


def build_users(rng: np.random.Generator) -> pd.DataFrame:
    users = []
    for i, name in enumerate(FIRST_NAMES):
        user_id = f"U{i + 1:03d}"
        if i < 12:
            role, can_post, can_approve = "AP Clerk", True, False
        elif i < 18:
            role, can_post, can_approve = "AP Manager", False, True
        elif i < 22:
            role, can_post, can_approve = "Finance Executive", True, False
        else:
            role, can_post, can_approve = "Financial Controller", True, True
        users.append((user_id, name, role, can_post, can_approve))
    users.append(("BATCH", "System batch job", "System", True, False))
    return pd.DataFrame(
        users, columns=["user_id", "name", "role", "can_post", "can_approve"]
    )


def next_weekday(ts: datetime) -> datetime:
    """Roll a timestamp forward off weekends (keeps planted duplicates/splits
    from doubling as off-hours exceptions)."""
    while ts.weekday() >= 5:
        ts += timedelta(days=1)
    return ts


def business_timestamp(rng: np.random.Generator) -> datetime:
    """A weekday timestamp during working hours (8:30-18:30)."""
    while True:
        day = FY_START + timedelta(days=int(rng.integers(0, 365)))
        if day.weekday() < 5:
            break
    seconds = int(rng.normal(loc=13 * 3600, scale=2.5 * 3600))
    seconds = min(max(seconds, int(8.5 * 3600)), int(18.5 * 3600))
    return day + timedelta(seconds=seconds)


def baseline_amount(rng: np.random.Generator) -> float:
    return float(np.clip(rng.lognormal(mean=8.3, sigma=1.25), 50, 480_000).round(2))


def main() -> None:
    rng = np.random.default_rng(SEED)
    users = build_users(rng)
    posters = users[users.can_post & (users.user_id != "BATCH")].user_id.to_numpy()
    approvers = users[users.can_approve].user_id.to_numpy()

    vendors = [(f"V{i + 1:03d}", name) for i, name in enumerate(VENDOR_NAMES)]
    rows: list[dict] = []
    truth: list[tuple[str, str]] = []
    counter = 0

    def add_row(ts, vendor, amount, posted_by=None, approved_by=None, anomaly=None, account=None):
        nonlocal counter
        counter += 1
        entry_id = f"JE{counter:06d}"
        vid, vname = vendor
        acct = account or ACCOUNTS[int(rng.integers(0, len(ACCOUNTS)))]
        if posted_by is None:
            posted_by = str(rng.choice(posters))
        if approved_by is None:
            candidates = [a for a in approvers if a != posted_by]
            approved_by = str(rng.choice(candidates))
        rows.append(
            {
                "entry_id": entry_id,
                "posting_ts": ts,
                "account_code": acct[0],
                "account_name": acct[1],
                "vendor_id": vid,
                "vendor_name": vname,
                "amount_rm": round(float(amount), 2),
                "posted_by": posted_by,
                "approved_by": approved_by,
                "doc_type": "AP invoice",
            }
        )
        if anomaly:
            truth.append((entry_id, anomaly))
        return entry_id

    # --- baseline population -------------------------------------------------
    for _ in range(N_BASELINE):
        add_row(business_timestamp(rng), vendors[int(rng.integers(0, len(vendors)))], baseline_amount(rng))

    # legitimate overnight batch runs (should NOT be flagged as off-hours)
    for _ in range(400):
        day = FY_START + timedelta(days=int(rng.integers(0, 365)))
        ts = day.replace(hour=2, minute=0) + timedelta(seconds=int(rng.integers(0, 3600)))
        add_row(ts, vendors[int(rng.integers(0, len(vendors)))], baseline_amount(rng), posted_by="BATCH")

    # --- planted exceptions ----------------------------------------------------

    # 1. Duplicate payments: same vendor + amount, days apart, different entries.
    for _ in range(12):
        vendor = vendors[int(rng.integers(0, len(vendors)))]
        amount = baseline_amount(rng)
        ts = business_timestamp(rng)
        add_row(ts, vendor, amount, anomaly="duplicate_payment")
        add_row(next_weekday(ts + timedelta(days=int(rng.integers(1, 5)))), vendor, amount,
                anomaly="duplicate_payment")

    # 2. Split invoices: clusters just under the RM 50,000 approval threshold.
    for _ in range(8):
        vendor = vendors[int(rng.integers(0, len(vendors)))]
        clerk = str(rng.choice(posters))
        ts = business_timestamp(rng)
        for j in range(int(rng.integers(2, 5))):
            amount = float(rng.uniform(0.90, 0.99)) * APPROVAL_THRESHOLD_RM
            add_row(next_weekday(ts + timedelta(days=j)), vendor, amount,
                    posted_by=clerk, anomaly="threshold_split")

    # 3. Off-hours postings by human users (small hours / weekends).
    for _ in range(30):
        day = FY_START + timedelta(days=int(rng.integers(0, 365)))
        if rng.random() < 0.5:  # night posting
            ts = day.replace(hour=int(rng.integers(0, 5)), minute=int(rng.integers(0, 60)))
        else:  # weekend posting
            ts = day + timedelta(days=(5 - day.weekday()) % 7, hours=int(rng.integers(9, 20)))
        add_row(ts, vendors[int(rng.integers(0, len(vendors)))], baseline_amount(rng), anomaly="off_hours")

    # 4. Segregation-of-duties breaks: self-approval or unauthorised approver.
    non_approvers = users[users.can_post & ~users.can_approve & (users.user_id != "BATCH")].user_id.to_numpy()
    for i in range(10):
        clerk = str(rng.choice(non_approvers))
        approved_by = clerk if i % 2 == 0 else str(rng.choice(non_approvers))
        add_row(business_timestamp(rng), vendors[int(rng.integers(0, len(vendors)))],
                baseline_amount(rng), posted_by=clerk, approved_by=approved_by, anomaly="sod_violation")

    # 5. Suspiciously round amounts concentrated on one vendor.
    round_vendor = vendors[7]
    for _ in range(25):
        amount = float(rng.choice([5_000, 10_000, 15_000, 20_000, 25_000]))
        add_row(business_timestamp(rng), round_vendor, amount, anomaly="round_amount")

    # 6. Fabricated invoices: one vendor whose amounts violate Benford's law
    #    (first digits pushed toward 7-9, as a fraudster keeping invoices
    #    "just under" review limits tends to produce).
    benford_vendor = vendors[33]
    for _ in range(400):
        first = float(rng.choice([7, 8, 9]))
        magnitude = float(rng.choice([100, 1_000, 10_000]))
        amount = first * magnitude * float(rng.uniform(1.0, 1.099))
        add_row(business_timestamp(rng), benford_vendor, amount, anomaly="benford_vendor")

    ledger = pd.DataFrame(rows).sample(frac=1.0, random_state=SEED).reset_index(drop=True)

    DATA_DIR.mkdir(exist_ok=True)
    ledger.to_csv(DATA_DIR / "journal_entries.csv", index=False)
    users.to_csv(DATA_DIR / "users.csv", index=False)
    pd.DataFrame(truth, columns=["entry_id", "anomaly_type"]).to_csv(
        DATA_DIR / "ground_truth.csv", index=False
    )
    print(f"[generate] {len(ledger):,} journal lines, {len(users)} users, "
          f"{len(truth)} planted exceptions -> data/")


if __name__ == "__main__":
    main()

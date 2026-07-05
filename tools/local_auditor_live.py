"""
Multi-source live public-money auditor for ReClaw 2.0.

Fetches data from USASpending, Census ACS, ProPublica nonprofits, and Indiana
Gateway disbursements (cache-first, live download fallback). Runs ensemble
forensic detectors and emits repo-native RedFlags for scriptwriter / county queue.

Categories align with tools/scriptwriter.py (dominant_disbursement, benford_*, etc.).
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from core.handoff import RedFlag
from tools.audit_adapter import COUNTY_CENSUS
from tools.public_data_loaders import REPO_ROOT

UA = "ReClaw/2.0 Local Auditor (+public records research)"
USASPEND = "https://api.usaspending.gov/api/v2"
CENSUS = "https://api.census.gov/data/2022/acs/acs5"
PROPUBLICA = "https://projects.propublica.org/nonprofits/api/v2"
GATEWAY_DL = "https://gateway.ifionline.org/public/download.aspx"

CACHE_DIR = REPO_ROOT / "data" / "cache"

SRC = {
    "usaspending": "https://api.usaspending.gov/",
    "census": "https://data.census.gov/",
    "propublica": "https://projects.propublica.org/nonprofits/",
    "gateway": GATEWAY_DL,
}

# Benford expected first-digit frequencies
_BENFORD = [0.301, 0.176, 0.125, 0.097, 0.079, 0.067, 0.058, 0.051, 0.046]


@dataclass
class AuditResult:
    county: str
    state: str = "IN"
    fips: str = ""
    gateway_code: int | None = None
    red_flags: list[RedFlag] = field(default_factory=list)
    census: dict = field(default_factory=dict)
    years_audited: list[int] = field(default_factory=list)
    total_rows: int = 0
    sources_used: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
def _http_json(url: str, payload: dict | None = None, *, timeout: int = 45) -> dict:
    headers = {"User-Agent": UA}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            if payload is None:
                r = client.get(url, headers=headers)
            else:
                r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        return {"_error": str(e)}


def _census_key() -> str | None:
    k = os.environ.get("CENSUS_API_KEY")
    if k:
        return k
    for name in (".env.local", ".env"):
        path = REPO_ROOT / name
        try:
            for line in path.read_text().splitlines():
                if line.startswith("CENSUS_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            pass
    return None


def _county_fips3(fips: str) -> str:
    """USASpending wants 3-digit county FIPS within state (e.g. 125 for Pike)."""
    digits = re.sub(r"\D", "", fips)
    if len(digits) >= 5:
        return digits[-3:]
    return digits.zfill(3)[-3:]


def _state_fips(fips: str) -> str:
    digits = re.sub(r"\D", "", fips)
    return digits[:2] if len(digits) >= 2 else "18"


# --------------------------------------------------------------------------- #
# Fetchers
# --------------------------------------------------------------------------- #
def fetch_fed_timeseries(
    state: str,
    county_fips3: str,
    *,
    start: str = "2008-01-01",
    end: str = "2024-12-31",
) -> pd.DataFrame:
    loc = {"country": "USA", "state": state.upper(), "county": county_fips3}
    r = _http_json(
        f"{USASPEND}/search/spending_over_time/",
        {
            "group": "fiscal_year",
            "filters": {
                "time_period": [{"start_date": start, "end_date": end}],
                "place_of_performance_locations": [loc],
            },
        },
    )
    rows = [
        {
            "fy": int(x["time_period"]["fiscal_year"]),
            "amount": float(x.get("aggregated_amount") or 0),
        }
        for x in r.get("results", [])
    ]
    return pd.DataFrame(rows).sort_values("fy").reset_index(drop=True) if rows else pd.DataFrame()


def fetch_fed_recipients(
    state: str,
    county_fips3: str,
    *,
    start: str = "2019-01-01",
    end: str = "2024-12-31",
    limit: int = 50,
) -> pd.DataFrame:
    loc = {"country": "USA", "state": state.upper(), "county": county_fips3}
    r = _http_json(
        f"{USASPEND}/search/spending_by_category/recipient/",
        {
            "filters": {
                "time_period": [{"start_date": start, "end_date": end}],
                "place_of_performance_locations": [loc],
            },
            "limit": limit,
        },
    )
    rows = [
        {"name": x.get("name"), "amount": float(x.get("amount") or 0)}
        for x in r.get("results", [])
    ]
    return pd.DataFrame(rows)


def fetch_fed_agencies(
    state: str,
    county_fips3: str,
    *,
    start: str = "2019-01-01",
    end: str = "2024-12-31",
    limit: int = 15,
) -> pd.DataFrame:
    loc = {"country": "USA", "state": state.upper(), "county": county_fips3}
    r = _http_json(
        f"{USASPEND}/search/spending_by_category/awarding_agency/",
        {
            "filters": {
                "time_period": [{"start_date": start, "end_date": end}],
                "place_of_performance_locations": [loc],
            },
            "limit": limit,
        },
    )
    rows = [
        {"agency": x.get("name"), "amount": float(x.get("amount") or 0)}
        for x in r.get("results", [])
    ]
    return pd.DataFrame(rows)


def fetch_fed_top_awards(
    state: str,
    county_fips3: str,
    *,
    start: str = "2019-01-01",
    end: str = "2024-12-31",
    limit: int = 15,
) -> pd.DataFrame:
    loc = {"country": "USA", "state": state.upper(), "county": county_fips3}
    r = _http_json(
        f"{USASPEND}/search/spending_by_award/",
        {
            "filters": {
                "time_period": [{"start_date": start, "end_date": end}],
                "place_of_performance_locations": [loc],
                "award_type_codes": ["02", "03", "04", "05", "A", "B", "C", "D"],
            },
            "fields": [
                "Award ID",
                "Recipient Name",
                "Award Amount",
                "Awarding Agency",
                "Description",
            ],
            "limit": limit,
            "sort": "Award Amount",
            "order": "desc",
        },
    )
    rows = [
        {
            "recipient": x.get("Recipient Name"),
            "amount": float(x.get("Award Amount") or 0),
            "agency": x.get("Awarding Agency"),
            "desc": x.get("Description"),
        }
        for x in r.get("results", [])
    ]
    return pd.DataFrame(rows)


def fetch_census(state_fips: str = "18", county_fips3: str = "125") -> dict:
    key = _census_key()
    if not key:
        return {"_error": "no CENSUS_API_KEY (free at api.census.gov/data/key_signup.html)"}
    vars_ = "NAME,B19013_001E,B17001_002E,B17001_001E,B01003_001E,B24011_001E"
    url = f"{CENSUS}?get={vars_}&for=county:{county_fips3}&in=state:{state_fips}&key={key}"
    r = _http_json(url, timeout=30)
    if "_error" in r:
        return r
    try:
        if not isinstance(r, list) or len(r) < 2:
            return {"_error": "unexpected census response"}
        h, v = r[0], r[1]
        d = dict(zip(h, v))
        pov = float(d["B17001_002E"])
        univ = float(d["B17001_001E"])
        return {
            "name": d["NAME"],
            "median_hh_income": float(d["B19013_001E"]),
            "median_earnings": float(d["B24011_001E"]),
            "population": int(float(d["B01003_001E"])),
            "poverty_rate_pct": round(pov / univ * 100, 1) if univ else None,
        }
    except Exception as e:
        return {"_error": str(e)}


def fetch_nonprofits(city: str = "Petersburg Indiana") -> pd.DataFrame:
    from urllib.parse import quote

    r = _http_json(f"{PROPUBLICA}/search.json?q={quote(city)}")
    if "_error" in r:
        return pd.DataFrame()
    orgs = [
        {
            "name": o.get("name"),
            "city": o.get("city"),
            "state": o.get("state"),
            "ein": o.get("ein"),
        }
        for o in r.get("organizations", [])
    ]
    return pd.DataFrame(orgs)


def fetch_gateway_disbursements(
    gateway_code: int,
    year: int = 2024,
    *,
    unit_type: str = "County",
    timeout: int = 90,
) -> tuple[pd.DataFrame, str]:
    """Live Gateway download filtered to one county. Returns (df, status_msg)."""
    from tools.indiana_gateway import download_disbursements

    cache_path = CACHE_DIR / f"gateway_disbursements_{year}.txt"
    try:
        if not cache_path.exists() or cache_path.stat().st_size < 1000:
            download_disbursements(year, cache_path, timeout=timeout)
        raw = cache_path.read_text(encoding="utf-8", errors="replace")
        df = pd.read_csv(StringIO(raw), sep="|", low_memory=False)
        if "cnty_cd" in df.columns:
            df = df[df["cnty_cd"].astype(str) == str(gateway_code)]
        return df, f"gateway cache ok: {len(df)} rows for cnty_cd={gateway_code} year={year}"
    except Exception as e:
        return pd.DataFrame(), f"gateway fetch failed: {e}"


# --------------------------------------------------------------------------- #
# Gateway cache helpers (fast path)
# --------------------------------------------------------------------------- #
def _fips_from_gateway(code: int) -> str:
    return f"18{2 * code - 1:03d}"


def _load_rows(gateway_code: int, year: int) -> list[dict]:
    path = CACHE_DIR / f"gateway_disbursements_{year}.txt"
    if not path.exists():
        return []
    out = []
    for row in csv.DictReader(StringIO(path.read_text()), delimiter="|"):
        try:
            if int(row.get("cnty_cd", 0)) == gateway_code:
                out.append(row)
        except ValueError:
            continue
    return out


def _amount(row: dict) -> float:
    try:
        return float(row.get("amount", 0) or 0)
    except ValueError:
        return 0.0


# --------------------------------------------------------------------------- #
# Detectors
# --------------------------------------------------------------------------- #
def _robust_zscore(values: list[float]) -> list[float]:
    if len(values) < 3:
        return [0.0] * len(values)
    arr = np.array(values, dtype=float)
    med = np.median(arr)
    mad = np.median(np.abs(arr - med))
    if mad < 1e-9:
        return [0.0] * len(values)
    return list(0.6745 * (arr - med) / mad)


def _benford_test(amounts: list[float]) -> tuple[float, bool, float]:
    """Return (max deviation, failed, chi_sq) for first-digit Benford test."""
    positives = [a for a in amounts if a >= 1.0]
    if len(positives) < 50:
        return 0.0, False, 0.0
    counts = [0] * 9
    for a in positives:
        d = int(str(int(a))[0])
        if 1 <= d <= 9:
            counts[d - 1] += 1
    n = sum(counts)
    if n < 50:
        return 0.0, False, 0.0
    max_dev = 0.0
    chi = 0.0
    for i, c in enumerate(counts):
        obs = c / n
        exp = _BENFORD[i]
        max_dev = max(max_dev, abs(obs - exp))
        if exp > 0:
            chi += (obs - exp) ** 2 / exp
    failed = max_dev >= 0.055 or chi >= 0.25
    return max_dev, failed, chi


def _round_number_cluster(amounts: list[float]) -> int:
    return sum(1 for a in amounts if a >= 1000 and int(a) % 1000 == 0)


def _vendor_fragmentation(by_vendor: dict[str, float], total: float) -> tuple[int, float]:
    """Count vendors with small payments that together exceed 15% (split-purchase signal)."""
    if total <= 0:
        return 0, 0.0
    small = [(v, a) for v, a in by_vendor.items() if 0 < a < 25_000]
    if len(small) < 5:
        return 0, 0.0
    small_sum = sum(a for _, a in small)
    return len(small), small_sum / total


def _detect_federal_flags(
    county_label: str,
    fed_ts: pd.DataFrame,
    fed_recipients: pd.DataFrame,
    fed_awards: pd.DataFrame,
) -> list[RedFlag]:
    flags: list[RedFlag] = []
    if fed_ts.empty or len(fed_ts) < 2:
        return flags

    amounts = fed_ts["amount"].tolist()
    years = fed_ts["fy"].tolist()
    zscores = _robust_zscore(amounts)

    if len(amounts) >= 2:
        y0, y1 = years[-2], years[-1]
        t0, t1 = amounts[-2], amounts[-1]
        if t0 > 0:
            chg = (t1 - t0) / t0 * 100
            if abs(chg) >= 20:
                flags.append(
                    RedFlag(
                        severity="high" if abs(chg) >= 35 else "medium",
                        category="federal_spending_spike",
                        description=(
                            f"{county_label}: federal awards in county {y0}→{y1} "
                            f"moved {chg:+.1f}% (${t0:,.0f} → ${t1:,.0f})"
                        ),
                        evidence=json.dumps(
                            {
                                "amount": abs(t1 - t0),
                                "total": t1,
                                "year": y1,
                                "source": "usaspending",
                            }
                        ),
                        recommended_action="Compare to local budget timing and grant announcements.",
                    )
                )

    if zscores and abs(zscores[-1]) >= 2.5:
        flags.append(
            RedFlag(
                severity="high" if abs(zscores[-1]) >= 3.5 else "medium",
                category="statistical_anomaly",
                description=(
                    f"{county_label}: latest federal spending (${amounts[-1]:,.0f} FY{years[-1]}) "
                    f"is a robust z-score outlier ({zscores[-1]:+.1f}σ vs prior years)"
                ),
                evidence=f"USASpending place-of-performance; z={zscores[-1]:.2f}; {SRC['usaspending']}",
                recommended_action="Pull award detail from USASpending.gov for the spike year.",
            )
        )

    if not fed_recipients.empty:
        top = fed_recipients.iloc[0]
        total = fed_recipients["amount"].sum()
        if total > 0 and float(top["amount"]) / total >= 0.45:
            flags.append(
                RedFlag(
                    severity="medium",
                    category="vendor_concentration",
                    description=(
                        f"Federal awards in {county_label}: '{top['name']}' received "
                        f"${float(top['amount']):,.0f} ({float(top['amount'])/total*100:.1f}% of tracked federal)"
                    ),
                    evidence=f"USASpending recipient rollup; {SRC['usaspending']}",
                    recommended_action="Verify whether concentration reflects a single infrastructure grant.",
                )
            )

    if not fed_awards.empty:
        top_aw = fed_awards.iloc[0]
        if float(top_aw["amount"]) >= 5_000_000:
            flags.append(
                RedFlag(
                    severity="high",
                    category="dominant_disbursement",
                    description=(
                        f"{county_label}: top federal award ${float(top_aw['amount']):,.0f} to "
                        f"'{top_aw['recipient']}' ({top_aw.get('agency') or 'federal agency'})"
                    ),
                    evidence=json.dumps(
                        {
                            "amount": float(top_aw["amount"]),
                            "source": "usaspending",
                            "recipient": str(top_aw["recipient"])[:80],
                        }
                    ),
                    recommended_action="Ask county commissioners how federal pass-through is booked locally.",
                )
            )

    return flags


def _detect_isolation_forest(
    county_label: str,
    year_features: list[dict],
) -> list[RedFlag]:
    if len(year_features) < 3:
        return []
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        return []

    cols = ["total", "vendor_count", "line_count", "round_pct"]
    X = np.array([[f.get(c, 0) for c in cols] for f in year_features], dtype=float)
    if X.std() < 1e-9:
        return []

    clf = IsolationForest(contamination=0.25, random_state=42)
    preds = clf.fit_predict(X)
    flags: list[RedFlag] = []
    for i, pred in enumerate(preds):
        if pred != -1:
            continue
        yr = year_features[i]["year"]
        flags.append(
            RedFlag(
                severity="high",
                category="statistical_anomaly",
                description=(
                    f"{county_label} FY{yr}: disbursement profile flagged by IsolationForest "
                    f"(unusual mix of totals, vendors, and round-number payments)"
                ),
                evidence=f"Gateway multi-year features; IsolationForest; {SRC['gateway']}",
                recommended_action="Compare FY profile to peer counties and prior-year mix.",
            )
        )
        break  # one IF flag per county is enough for scriptwriter
    return flags


def _detect_cross_source(
    county_label: str,
    census: dict,
    gateway_total: float,
    fed_total: float,
) -> list[RedFlag]:
    flags: list[RedFlag] = []
    pop = census.get("population") or 0
    income = census.get("median_hh_income") or census.get("median_earnings") or 0

    if pop > 0 and gateway_total > 0:
        per_capita = gateway_total / pop
        if per_capita >= 2_500:
            flags.append(
                RedFlag(
                    severity="medium",
                    category="composition_outlier",
                    description=(
                        f"{county_label}: local disbursements ≈ ${per_capita:,.0f} per resident "
                        f"(${gateway_total:,.0f} total / {pop:,} people)"
                    ),
                    evidence=f"Census population + Gateway disbursements; {SRC['census']}",
                    recommended_action="Compare per-capita spend to neighboring counties.",
                )
            )

    if income > 0 and fed_total > 0 and fed_total > income * pop * 0.5:
        flags.append(
            RedFlag(
                severity="medium",
                category="federal_spending_spike",
                description=(
                    f"{county_label}: federal awards (${fed_total:,.0f}) dwarf typical "
                    f"household economics (median income ${income:,.0f})"
                ),
                evidence=f"USASpending + Census ACS contrast; {SRC['usaspending']}",
                recommended_action="Identify whether federal dollars are pass-through or direct county receipts.",
            )
        )
    return flags


def _gateway_year_flags(
    county_label: str,
    gateway_code: int,
    year: int,
    rows: list[dict],
) -> list[RedFlag]:
    flags: list[RedFlag] = []
    if not rows:
        return flags

    year_sum = sum(_amount(r) for r in rows)
    total = max(year_sum, 1)
    all_amounts = [_amount(r) for r in rows if _amount(r) > 0]

    by_line: dict[str, float] = defaultdict(float)
    by_vendor: dict[str, float] = defaultdict(float)
    by_fund: dict[str, float] = defaultdict(float)
    for r in rows:
        amt = _amount(r)
        line = (r.get("disburse_name") or r.get("class_name") or "unknown").strip()
        vendor = (r.get("ent_name") or r.get("unit_name") or "unknown").strip()
        fund = (r.get("fund_name") or "unknown").strip()
        by_line[line] += amt
        by_vendor[vendor] += amt
        by_fund[fund] += amt

    if by_line:
        top_line, top_amt = max(by_line.items(), key=lambda x: x[1])
        share = top_amt / total
        if top_amt >= 250_000 and share >= 0.08:
            flags.append(
                RedFlag(
                    severity="critical" if top_amt >= 5_000_000 else "high",
                    category="dominant_disbursement",
                    description=(
                        f"{county_label} FY{year}: '{top_line}' = ${top_amt:,.0f} "
                        f"({share*100:.1f}% of ${total:,.0f} disbursements)"
                    ),
                    evidence=json.dumps(
                        {
                            "amount": top_amt,
                            "year": year,
                            "source": "gateway",
                            "cnty_cd": gateway_code,
                            "line": top_line[:80],
                        }
                    ),
                    recommended_action="Ask commissioners to explain this line at a public meeting.",
                )
            )

    if by_vendor:
        top_v, top_v_amt = max(by_vendor.items(), key=lambda x: x[1])
        vshare = top_v_amt / total
        if vshare >= 0.35 and top_v_amt >= 500_000:
            flags.append(
                RedFlag(
                    severity="high" if vshare >= 0.5 else "medium",
                    category="vendor_concentration",
                    description=(
                        f"'{top_v}' received ${top_v_amt:,.0f} ({vshare*100:.1f}% of "
                        f"{county_label} FY{year} disbursements)"
                    ),
                    evidence=f"Gateway vendor aggregation cnty_cd={gateway_code} year={year}",
                    recommended_action="Review bid/procurement records for vendor concentration.",
                )
            )

        n_small, small_share = _vendor_fragmentation(by_vendor, total)
        if n_small >= 15 and small_share >= 0.15:
            flags.append(
                RedFlag(
                    severity="medium",
                    category="split_purchase_pattern",
                    description=(
                        f"{county_label} FY{year}: {n_small} sub-$25K payments total "
                        f"{small_share*100:.1f}% of disbursements (fragmentation signal)"
                    ),
                    evidence=f"Gateway vendor fragmentation cnty_cd={gateway_code} year={year}",
                    recommended_action="Check for bid-threshold splitting per IC 36-1-12-19.",
                )
            )

    if len(by_fund) >= 3:
        top_fund, fund_amt = max(by_fund.items(), key=lambda x: x[1])
        fshare = fund_amt / total
        if fshare >= 0.45 and fund_amt >= 1_000_000:
            flags.append(
                RedFlag(
                    severity="medium",
                    category="composition_outlier",
                    description=(
                        f"{county_label} FY{year}: fund '{top_fund}' holds ${fund_amt:,.0f} "
                        f"({fshare*100:.1f}% of all disbursements)"
                    ),
                    evidence=f"Gateway fund_name aggregation year={year}",
                    recommended_action="Compare fund mix to prior years and budget certification.",
                )
            )

    if all_amounts:
        dev, failed, chi = _benford_test(all_amounts)
        if failed:
            flags.append(
                RedFlag(
                    severity="high",
                    category="benford_violation",
                    description=(
                        f"{county_label} FY{year}: disbursement amounts show Benford deviation "
                        f"(max skew {dev:.3f}, χ²={chi:.3f} across {len(all_amounts)} payments)"
                    ),
                    evidence=f"Benford first-digit test on Gateway disbursements, cnty_cd={gateway_code}",
                    recommended_action="Forensic review of disbursement ledger — smoke test, not proof of fraud.",
                )
            )

        rounds = _round_number_cluster(all_amounts)
        if rounds >= 25:
            flags.append(
                RedFlag(
                    severity="medium",
                    category="round_number_cluster",
                    description=(
                        f"{county_label} FY{year}: {rounds} disbursements are suspiciously round "
                        f"(whole thousands of dollars)"
                    ),
                    evidence=f"Gateway amount pattern scan cnty_cd={gateway_code}",
                    recommended_action="Sample round-check payments for supporting documentation.",
                )
            )

    return flags


def _dedupe_flags(flags: list[RedFlag]) -> list[RedFlag]:
    seen: set[str] = set()
    unique: list[RedFlag] = []
    for f in flags:
        key = f"{f.category}:{f.description[:100]}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)
    return unique


# --------------------------------------------------------------------------- #
# Main audit
# --------------------------------------------------------------------------- #
def audit_county(
    state: str,
    fips: str,
    county_label: str,
    *,
    gateway_code: int | None = None,
    years: list[int] | None = None,
    county_seat: str | None = None,
) -> AuditResult:
    """
    Full multi-source audit for one Indiana county.

    county_label: e.g. "Pike County"
    fips: e.g. "18125" (optional if gateway_code provided)
    """
    state = state.upper()
    name = county_label.replace(" County", "").strip()
    sources_used: list[str] = []

    if gateway_code is None and fips.startswith("18"):
        try:
            gateway_code = (int(fips) - 18000 + 1) // 2
        except ValueError:
            gateway_code = None

    if gateway_code is None:
        return AuditResult(
            county=county_label,
            state=state,
            fips=fips,
            red_flags=[
                RedFlag(
                    severity="medium",
                    category="data_gap",
                    description=f"Cannot resolve Gateway code for {county_label}.",
                    evidence=f"fips={fips}",
                )
            ],
        )

    if not fips:
        fips = _fips_from_gateway(gateway_code)

    county_fips3 = _county_fips3(fips)
    state_fips = _state_fips(fips)

    # Census (live or embedded fallback)
    census = fetch_census(state_fips, county_fips3)
    if "_error" not in census:
        sources_used.append("census")
    else:
        census = dict(COUNTY_CENSUS.get(name, {}))
        if census:
            sources_used.append("census_embedded")

    # Federal awards
    fed_ts = fetch_fed_timeseries(state, county_fips3)
    fed_recipients = fetch_fed_recipients(state, county_fips3)
    fed_awards = fetch_fed_top_awards(state, county_fips3)
    if not fed_ts.empty:
        sources_used.append("usaspending")

    # Nonprofits (informational — thin counties may have none)
    seat = county_seat or f"{name} Indiana"
    nonprofits = fetch_nonprofits(seat)
    if not nonprofits.empty:
        sources_used.append("propublica")

    # Gateway years from cache
    years = years or [
        y
        for y in (2022, 2023, 2024, 2025)
        if (CACHE_DIR / f"gateway_disbursements_{y}.txt").exists()
    ]
    if not years:
        years = [2024]
        fetch_gateway_disbursements(gateway_code, 2024)
    if any((CACHE_DIR / f"gateway_disbursements_{y}.txt").exists() for y in years):
        sources_used.append("gateway")

    flags: list[RedFlag] = []
    total_rows = 0
    year_totals: dict[int, float] = {}
    year_features: list[dict] = []

    for year in years:
        rows = _load_rows(gateway_code, year)
        if not rows and year == max(years):
            df, _msg = fetch_gateway_disbursements(gateway_code, year)
            if not df.empty:
                rows = df.to_dict("records")
        total_rows += len(rows)
        year_sum = sum(_amount(r) for r in rows)
        year_totals[year] = year_sum

        flags.extend(_gateway_year_flags(county_label, gateway_code, year, rows))

        if rows:
            amts = [_amount(r) for r in rows if _amount(r) > 0]
            vendors = {
                (r.get("ent_name") or r.get("unit_name") or "unknown").strip()
                for r in rows
            }
            lines = {
                (r.get("disburse_name") or r.get("class_name") or "unknown").strip()
                for r in rows
            }
            round_pct = _round_number_cluster(amts) / max(len(amts), 1)
            year_features.append(
                {
                    "year": year,
                    "total": year_sum,
                    "vendor_count": len(vendors),
                    "line_count": len(lines),
                    "round_pct": round_pct,
                }
            )

    # YoY local disbursement swing
    sorted_years = sorted(year_totals.keys())
    if len(sorted_years) >= 2:
        y0, y1 = sorted_years[-2], sorted_years[-1]
        t0, t1 = year_totals[y0], year_totals[y1]
        if t0 > 0:
            chg = (t1 - t0) / t0 * 100
            if abs(chg) >= 15:
                flags.append(
                    RedFlag(
                        severity="high" if abs(chg) >= 25 else "medium",
                        category="disbursement_swing",
                        description=(
                            f"{county_label} total disbursements {y0}→{y1}: {chg:+.1f}% "
                            f"(${t0:,.0f} → ${t1:,.0f})"
                        ),
                        evidence=json.dumps(
                            {"amount": abs(t1 - t0), "total": t1, "year": y1, "source": "gateway"}
                        ),
                        recommended_action="Compare to certified budget and federal grant timing.",
                    )
                )

    # Ensemble + cross-source
    flags.extend(_detect_federal_flags(county_label, fed_ts, fed_recipients, fed_awards))
    flags.extend(_detect_isolation_forest(county_label, year_features))

    latest_gateway = year_totals.get(max(year_totals), 0) if year_totals else 0
    fed_latest = float(fed_ts["amount"].iloc[-1]) if not fed_ts.empty else 0.0
    flags.extend(_detect_cross_source(county_label, census, latest_gateway, fed_latest))

    if not nonprofits.empty and len(nonprofits) >= 3:
        flags.append(
            RedFlag(
                severity="low",
                category="nonprofit_presence",
                description=(
                    f"{county_label} area: {len(nonprofits)} nonprofits in ProPublica index "
                    f"(e.g. '{nonprofits.iloc[0]['name']}')"
                ),
                evidence=f"ProPublica nonprofit search; {SRC['propublica']}",
                recommended_action="Cross-check large local grants against 990 officer compensation.",
            )
        )

    if not flags:
        flags.append(
            RedFlag(
                severity="low",
                category="baseline",
                description=(
                    f"{county_label}: multi-source scan found no dominant patterns "
                    f"({total_rows:,} gateway rows)."
                ),
                evidence=f"sources={sources_used}",
            )
        )

    return AuditResult(
        county=county_label,
        state=state,
        fips=fips,
        gateway_code=gateway_code,
        red_flags=_dedupe_flags(flags),
        census=census,
        years_audited=years,
        total_rows=total_rows,
        sources_used=sources_used,
    )


def audit_county_by_name(county_name: str, *, gateway_code: int | None = None) -> AuditResult:
    """Convenience: audit by short name ('Pike') using worklist or FIPS formula."""
    if gateway_code is None:
        wl = REPO_ROOT / "data" / "indiana_county_worklist.yaml"
        if wl.exists():
            import yaml

            data = yaml.safe_load(wl.read_text())
            for c in data.get("counties", []):
                if c.get("name", "").lower() == county_name.lower():
                    return audit_county(
                        "IN",
                        c.get("fips", ""),
                        f"{county_name} County",
                        gateway_code=c.get("gateway_code"),
                        county_seat=c.get("county_seat_hint"),
                    )

    label = f"{county_name} County" if not county_name.endswith("County") else county_name
    return audit_county(
        "IN",
        _fips_from_gateway(gateway_code) if gateway_code else "",
        label,
        gateway_code=gateway_code,
    )


def to_compliance_package(result: AuditResult):
    """Convert AuditResult → CompliancePackage for orchestrator handoff."""
    from core.handoff import CompliancePackage

    high = sum(1 for f in result.red_flags if f.severity in ("critical", "high"))
    risk = min(10.0, 2.0 + high * 1.8 + len(result.red_flags) * 0.4)
    return CompliancePackage(
        county=result.county.replace(" County", ""),
        red_flags=result.red_flags,
        overall_risk_score=round(risk, 1),
        summary=(
            f"Local auditor ({', '.join(result.sources_used) or 'gateway'}): "
            f"{len(result.red_flags)} flags across {len(result.years_audited)} years "
            f"({result.total_rows:,} rows)."
        ),
        source_file=str(CACHE_DIR),
        total_records_audited=result.total_rows,
    )
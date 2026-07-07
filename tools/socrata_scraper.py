"""
Socrata Open Data API (SODA) scraper for municipal vendor/checkbook ledgers.

Indiana county factory uses Gateway flat files — use Socrata when a city/county
publishes AP data on a SODA portal (e.g. Bloomington, Chicago reference datasets).

Output lands in data/inbox/ for transaction_anomaly + benford_analysis.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
import pandas as pd

from tools.public_data_loaders import REPO_ROOT

INBOX = REPO_ROOT / "data" / "inbox"
CACHE = REPO_ROOT / "data" / "cache" / "socrata"
SOURCES = REPO_ROOT / "data" / "socrata_sources.yaml"

# Common amount column names after SODA export
_AMOUNT_ALIASES = ("amount", "payment_amount", "check_amount", "invoice_amount", "total")


class SocrataScraper:
    """Paginated SODA JSON fetcher."""

    def __init__(
        self,
        domain: str,
        dataset_id: str,
        *,
        app_token: str | None = None,
        timeout_s: float = 60.0,
    ):
        self.domain = domain.replace("https://", "").replace("http://", "").strip("/")
        self.dataset_id = dataset_id.strip()
        self.base_url = f"https://{self.domain}/resource/{self.dataset_id}.json"
        self.headers: dict[str, str] = {"Accept": "application/json"}
        if app_token:
            self.headers["X-App-Token"] = app_token
        self.timeout_s = timeout_s

    def fetch_page(
        self,
        *,
        limit: int = 50000,
        offset: int = 0,
        where: str | None = None,
        order: str = ":id",
        select: str | None = None,
    ) -> list[dict]:
        params: dict[str, Any] = {"$limit": limit, "$offset": offset, "$order": order}
        if where:
            params["$where"] = where
        if select:
            params["$select"] = select

        with httpx.Client(timeout=self.timeout_s, follow_redirects=True) as client:
            r = client.get(self.base_url, headers=self.headers, params=params)
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else []

    def fetch_all(
        self,
        *,
        page_size: int = 50000,
        max_records: int | None = None,
        where: str | None = None,
        sleep_s: float = 0.5,
        progress: bool = True,
    ) -> pd.DataFrame:
        all_records: list[dict] = []
        offset = 0
        if max_records:
            page_size = min(page_size, max_records)

        while True:
            req_limit = page_size
            if max_records:
                req_limit = min(page_size, max_records - len(all_records))
            try:
                batch = self.fetch_page(limit=req_limit, offset=offset, where=where)
            except httpx.HTTPError as exc:
                if progress:
                    print(f"\n[!] HTTP error at offset {offset}: {exc}")
                break

            if not batch:
                break

            all_records.extend(batch)
            offset += page_size

            if progress:
                print(f"\rDownloaded {len(all_records)} records...", end="", flush=True)

            if max_records and len(all_records) >= max_records:
                all_records = all_records[:max_records]
                if progress:
                    print(f"\n[+] Reached max_records={max_records}")
                break

            if len(batch) < page_size:
                break

            time.sleep(sleep_s)

        if progress and all_records:
            print(f"\n[+] Total: {len(all_records)} records")
        return pd.DataFrame(all_records)


def _guess_amount_column(df: pd.DataFrame) -> str | None:
    lower = {c.lower().replace(" ", "_"): c for c in df.columns}
    for alias in _AMOUNT_ALIASES:
        if alias in lower:
            return lower[alias]
    for col in df.columns:
        if any(k in col.lower() for k in ("amount", "payment", "check")):
            return col
    return None


def save_scrape(
    df: pd.DataFrame,
    *,
    domain: str,
    dataset_id: str,
    output: Path | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    """Write CSV to inbox + manifest JSON."""
    INBOX.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    slug = (label or dataset_id).replace("/", "_")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    csv_path = output or INBOX / f"socrata_{slug}_{ts}.csv"
    df.to_csv(csv_path, index=False)

    amount_col = _guess_amount_column(df)
    manifest = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "dataset_id": dataset_id,
        "rows": len(df),
        "csv_path": str(csv_path),
        "columns": list(df.columns),
        "amount_column": amount_col,
        "file_kind": "ap_register" if amount_col else "generic",
    }
    manifest_path = CACHE / f"{slug}_{ts}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def analyze_scrape(manifest: dict[str, Any]) -> dict[str, Any]:
    """Optional Benford pass on scraped CSV."""
    amount_col = manifest.get("amount_column")
    csv_path = manifest.get("csv_path")
    if not amount_col or not csv_path:
        return {"benford": None, "reason": "no amount column detected"}

    from tools.benford_analysis import analyze_csv_column, format_report

    result = analyze_csv_column(csv_path, amount_col)
    return {"benford": result, "report": format_report(result)}


def load_sources() -> list[dict]:
    if not SOURCES.exists():
        return []
    import yaml

    data = yaml.safe_load(SOURCES.read_text()) or {}
    return data.get("datasets", [])
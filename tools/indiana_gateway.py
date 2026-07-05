"""
Indiana Gateway (IFI Online) — download public disbursement flat files.

Source: https://gateway.ifionline.org/public/download.aspx
Report: Annual Financial Reports → Disbursements by Fund
"""

from __future__ import annotations

from pathlib import Path

import httpx
from bs4 import BeautifulSoup

URL = "https://gateway.ifionline.org/public/download.aspx"
USER_AGENT = "ReClaw/2.0 (+rural public data research)"


def _form_values(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    def _val(field_id: str) -> str:
        el = soup.find("input", {"id": field_id})
        return el["value"] if el and el.get("value") else ""

    return {
        "__VIEWSTATE": _val("__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": _val("__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION": _val("__EVENTVALIDATION"),
    }


def download_disbursements(year: int, target_path: Path, timeout: int = 90) -> Path:
    """
    Download Indiana Gateway 'Disbursements by Fund' flat file for `year`.
    Saves pipe-delimited text to target_path.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(URL, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()

        payload = {
            **_form_values(response.text),
            "ctl00$ContentPlaceHolder1$RadComboBox1": "Annual Financial Reports",
            "ctl00$ContentPlaceHolder1$RadComboBox2": "Disbursements by Fund",
            "ctl00$ContentPlaceHolder1$DropDownListUnitType": "All",
            "ctl00$ContentPlaceHolder1$DropDownListYear": str(year),
            "ctl00$ContentPlaceHolder1$button_download1": "Download",
        }

        res = client.post(
            URL,
            data=payload,
            headers={"User-Agent": USER_AGENT, "Referer": URL},
        )
        res.raise_for_status()

        content = res.content
        if len(content) < 500 or b"<!DOCTYPE" in content[:200].upper():
            raise RuntimeError(
                f"Gateway returned HTML or tiny payload ({len(content)} bytes) for year {year}"
            )

        target_path.write_bytes(content)

    return target_path
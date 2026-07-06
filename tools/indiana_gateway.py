"""
Indiana Gateway (IFI Online) — download public flat files for all IN counties.

Source: https://gateway.ifionline.org/public/download.aspx
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


def download_gateway_file(
    *,
    dataset: str,
    file_type: str,
    year: int,
    unit_type: str = "All",
    target_path: Path,
    timeout: int = 180,
) -> Path:
    """
    Generic Gateway download (pipe-delimited flat file).

    Examples:
      dataset="Annual Financial Reports", file_type="Disbursements by Fund"
      dataset="Budget Data", file_type="Disbursements by Fund"  # statewide certified budgets
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(URL, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()

        payload = {
            **_form_values(response.text),
            "ctl00$ContentPlaceHolder1$RadComboBox1": dataset,
            "ctl00$ContentPlaceHolder1$RadComboBox2": file_type,
            "ctl00$ContentPlaceHolder1$DropDownListUnitType": unit_type,
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
                f"Gateway returned HTML or tiny payload ({len(content)} bytes) "
                f"for {dataset}/{file_type} year={year}"
            )

        target_path.write_bytes(content)

    return target_path


def download_disbursements(year: int, target_path: Path, timeout: int = 90) -> Path:
    """Download statewide 'Disbursements by Fund' flat file for `year`."""
    return download_gateway_file(
        dataset="Annual Financial Reports",
        file_type="Disbursements by Fund",
        year=year,
        target_path=target_path,
        timeout=timeout,
    )


def download_budget_data(year: int, target_path: Path, timeout: int = 180) -> Path:
    """
    Download statewide certified Gateway budget data for `year`.

    Note: Gateway UI labels this dataset 'Budget Data'; file layout matches
    DLGF budget certification (fund-level adopted estimates for every unit).
    """
    return download_gateway_file(
        dataset="Budget Data",
        file_type="Disbursements by Fund",
        year=year,
        target_path=target_path,
        timeout=timeout,
    )
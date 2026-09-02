"""
Export Indiana Gateway Employee Compensation CSV for one county.

Uses ReportViewer ASP.NET postbacks (httpx) — no browser required.
Cache: data/cache/salaries/salary_{gateway_code}_{year}.csv

Adapted from public-salaries/in_salaries (2012–2017 scraper), updated for 2025.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

from tools.county_data_fetch import resolve_county
from tools.indiana_gateway_salary import SALARY_CACHE_DIR, _salary_cache_path, parse_salary_export
from tools.public_data_loaders import REPO_ROOT

BASE_URL = "https://gateway.ifionline.org/report_builder/Default3a.aspx"
EXPORT_URL = "https://gateway.ifionline.org/Reserved.ReportViewerWebControl.axd"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def _parse_options(html: str, select_id: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    sel = soup.find("select", id=select_id)
    if not sel:
        return []
    out: list[dict[str, str]] = []
    for opt in sel.find_all("option"):
        val = opt.get("value", "")
        text = (opt.get_text() or "").replace("\xa0", " ").strip()
        if val and val != "0" and text and not text.startswith("<Select"):
            out.append({"text": text, "value": val})
    return out


def _extract_form_fields(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    fields: dict[str, str] = {}
    for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
        el = soup.find("input", id=name)
        if el and el.get("value"):
            fields[name] = el["value"]
    for script in soup.find_all("script"):
        txt = script.string or script.get_text() or ""
        if "ControlID=" in txt:
            m = re.search(r"ControlID=([A-Za-z0-9]+)", txt)
            if m:
                fields["ControlID"] = m.group(1)
            break
    return fields


def _base_params() -> dict[str, str]:
    return {
        "rptType": "employComp",
        "rpt": "EmployComp",
        "rptName": "Employee Compensation",
    }


def _report_form(
    form: dict[str, str],
    *,
    year_value: str,
    county_value: str,
    unit_value: str = "0",
    event_target: str = "",
    script_manager: str = "",
    view_report: bool = False,
    async_load: bool = False,
) -> dict[str, str]:
    data = {
        "ScriptManager1": script_manager or "ScriptManager1|ReportViewer1$ctl04$ctl00",
        "ScriptManager1_HiddenField": "",
        "ReportViewer1$ctl03$ctl00": "",
        "ReportViewer1$ctl03$ctl01": "",
        "ReportViewer1$ctl10": "ltr",
        "ReportViewer1$ctl11": "standards",
        "ReportViewer1$AsyncWait$HiddenCancelField": "False",
        "ReportViewer1$ctl04$ctl03$ddValue": year_value,
        "ReportViewer1$ctl04$ctl05$ddValue": county_value,
        "ReportViewer1$ctl04$ctl07$ddValue": unit_value,
        "ReportViewer1$ToggleParam$store": "",
        "ReportViewer1$ToggleParam$collapse": "false",
        "ReportViewer1$ctl08$ClientClickedId": "",
        "ReportViewer1$ctl07$store": "",
        "ReportViewer1$ctl07$collapse": "false",
        "ReportViewer1$ctl09$VisibilityState$ctl00": "None",
        "ReportViewer1$ctl09$ScrollPosition": "",
        "ReportViewer1$ctl09$ReportControl$ctl02": "",
        "ReportViewer1$ctl09$ReportControl$ctl03": "",
        "ReportViewer1$ctl09$ReportControl$ctl04": "100",
        "__EVENTTARGET": event_target,
        "__EVENTARGUMENT": "",
        "__LASTFOCUS": "",
        "__VIEWSTATE": form.get("__VIEWSTATE", ""),
        "__VIEWSTATEGENERATOR": form.get("__VIEWSTATEGENERATOR", ""),
        "__SCROLLPOSITIONX": "0",
        "__SCROLLPOSITIONY": "0",
        "__EVENTVALIDATION": form.get("__EVENTVALIDATION", ""),
        "__ASYNCPOST": "true",
    }
    if view_report:
        data["ReportViewer1$ctl05$ctl00$CurrentPage"] = "1"
        data["ReportViewer1$ctl04$ctl00"] = "View Report"
    elif async_load:
        data["ReportViewer1$ctl05$ctl00$CurrentPage"] = ""
        data["__EVENTTARGET"] = "ReportViewer1$ctl09$Reserved_AsyncLoadTarget"
        data["ScriptManager1"] = "ScriptManager1|ReportViewer1$ctl09$Reserved_AsyncLoadTarget"
    else:
        data["ReportViewer1$ctl05$ctl00$CurrentPage"] = ""
    return data


class GatewaySalaryExporter:
    def __init__(self, timeout: float = 90.0):
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        self.form: dict[str, str] = {}

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> GatewaySalaryExporter:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def bootstrap(self) -> dict[str, list[dict[str, str]]]:
        r = self.client.get(BASE_URL, params=_base_params())
        r.raise_for_status()
        self.form = _extract_form_fields(r.text)
        return {
            "years": _parse_options(r.text, "ReportViewer1_ctl04_ctl03_ddValue"),
            "counties": _parse_options(r.text, "ReportViewer1_ctl04_ctl05_ddValue"),
            "units": _parse_options(r.text, "ReportViewer1_ctl04_ctl07_ddValue"),
        }

    def _post(self, data: dict[str, str]) -> httpx.Response:
        self.client.headers["Origin"] = "https://gateway.ifionline.org"
        self.client.headers["Referer"] = str(httpx.URL(BASE_URL).copy_merge_params(_base_params()))
        self.client.headers["X-Requested-With"] = "XMLHttpRequest"
        self.client.headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        return self.client.post(BASE_URL, params=_base_params(), data=data)

    def select_county(self, year_value: str, county_value: str) -> list[dict[str, str]]:
        data = _report_form(
            self.form,
            year_value=year_value,
            county_value=county_value,
            event_target="ReportViewer1$ctl04$ctl05$ddValue",
            script_manager="ScriptManager1|ReportViewer1$ctl04$ctl05$ddValue",
        )
        r = self._post(data)
        r.raise_for_status()
        self.form.update(_extract_form_fields(r.text))
        return _parse_options(r.text, "ReportViewer1_ctl04_ctl07_ddValue")

    def _capture_report_session(self, html: str) -> None:
        """Pull ReportSession + export ControlID from loaded ReportViewer markup."""
        m_sess = re.search(r"ReportSession=([a-z0-9]+)", html)
        m_ctrl = re.search(
            r"ReportStack=1&ControlID=([a-f0-9]+)&OpType=Export", html, re.IGNORECASE
        )
        if m_sess:
            self.form["ReportSession"] = m_sess.group(1)
        if m_ctrl:
            self.form["ControlID"] = m_ctrl.group(1)

    def view_report(self, year_value: str, county_value: str, unit_value: str) -> None:
        data = _report_form(
            self.form,
            year_value=year_value,
            county_value=county_value,
            unit_value=unit_value,
            view_report=True,
        )
        r = self._post(data)
        r.raise_for_status()
        self.form.update(_extract_form_fields(r.text))
        self._capture_report_session(r.text)

    def async_load(self, year_value: str, county_value: str, unit_value: str) -> None:
        data = _report_form(
            self.form,
            year_value=year_value,
            county_value=county_value,
            unit_value=unit_value,
            async_load=True,
        )
        r = self._post(data)
        r.raise_for_status()
        self.form.update(_extract_form_fields(r.text))
        self._capture_report_session(r.text)

    def export_csv(self) -> bytes:
        if not self.form.get("ReportSession"):
            raise RuntimeError("ReportSession missing — report may not be loaded")
        if not self.form.get("ControlID"):
            raise RuntimeError("ReportViewer ControlID missing — report may not be loaded")
        params = {
            "ReportSession": self.form["ReportSession"],
            "Culture": "1033",
            "CultureOverrides": "True",
            "UICulture": "1033",
            "UICultureOverrides": "True",
            "ReportStack": "1",
            "ControlID": self.form["ControlID"],
            "OpType": "Export",
            "FileName": "SalarySearch",
            "ContentDisposition": "OnlyHtmlInline",
            "Format": "CSV",
        }
        r = self.client.get(EXPORT_URL, params=params)
        r.raise_for_status()
        if len(r.content) < 200 or b"Textbox6" not in r.content:
            raise RuntimeError(f"Unexpected export payload ({len(r.content)} bytes)")
        return r.content


def _match_county(counties: list[dict[str, str]], name: str) -> dict[str, str] | None:
    target = name.replace(" County", "").strip().lower()
    for c in counties:
        if c["text"].replace("\xa0", " ").strip().lower() == target:
            return c
    for c in counties:
        if target in c["text"].lower():
            return c
    return None


def _match_year(years: list[dict[str, str]], year: int) -> dict[str, str] | None:
    for y in years:
        if y["text"] == str(year):
            return y
    return years[0] if years else None


def _pick_county_unit(units: list[dict[str, str]], county_name: str) -> dict[str, str] | None:
    """Prefer the main county reporting unit (e.g. 'Spencer County')."""
    target = county_name.replace(" County", "").strip().lower()
    for u in units:
        t = u["text"].lower()
        if t == f"{target} county" or t == target:
            return u
    for u in units:
        if target in u["text"].lower() and "county" in u["text"].lower():
            return u
    return units[0] if units else None


def export_county_salary(
    county_name: str,
    *,
    gateway_code: int | None = None,
    year: int = 2025,
    force: bool = False,
) -> tuple[Path | None, str]:
    """
    Download Gateway Employee Compensation CSV for one county.
    Returns (cache_path, status_message).
    """
    meta = resolve_county(county_name) or {}
    gateway_code = gateway_code or meta.get("gateway_code")
    if not gateway_code:
        return None, f"Unknown county: {county_name}"

    out = _salary_cache_path(gateway_code, year)
    if out.exists() and out.stat().st_size > 200 and not force:
        n = len(parse_salary_export(out))
        return out, f"cache hit: {out.name} ({n} records)"

    name = county_name.replace(" County", "").strip()

    try:
        with GatewaySalaryExporter() as exp:
            lists = exp.bootstrap()
            county_opt = _match_county(lists["counties"], name)
            year_opt = _match_year(lists["years"], year)
            if not county_opt:
                return None, f"County '{name}' not found in Gateway dropdown"
            if not year_opt:
                return None, f"Year {year} not available in Gateway"

            units = exp.select_county(year_opt["value"], county_opt["value"])
            if not units:
                units = lists.get("units") or []
            unit_opt = _pick_county_unit(units, name)
            if not unit_opt:
                return None, f"No reporting unit for {name} County"

            exp.view_report(year_opt["value"], county_opt["value"], unit_opt["value"])
            exp.async_load(year_opt["value"], county_opt["value"], unit_opt["value"])
            content = exp.export_csv()

        SALARY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        out.write_bytes(content)
        n = len(parse_salary_export(out))
        return out, f"exported {out.name} ({n} records) from Gateway ReportViewer"
    except Exception as e:
        return None, f"Gateway salary export failed for {name}: {e}"


def prefetch_worklist_salaries(
    *,
    year: int = 2025,
    limit: int | None = None,
    skip_cached: bool = True,
) -> list[dict[str, str]]:
    """Batch export salaries for worklist counties."""
    import yaml

    wl = REPO_ROOT / "data" / "indiana_county_worklist.yaml"
    counties = yaml.safe_load(wl.read_text()).get("counties", [])
    results: list[dict[str, str]] = []
    for i, c in enumerate(counties):
        if limit is not None and i >= limit:
            break
        name = c["name"]
        code = c["gateway_code"]
        cache = _salary_cache_path(code, year)
        if skip_cached and cache.exists() and cache.stat().st_size > 200:
            results.append({"county": name, "status": "cached", "path": str(cache)})
            continue
        path, msg = export_county_salary(name, gateway_code=code, year=year)
        results.append({"county": name, "status": "ok" if path else "fail", "message": msg})
    return results
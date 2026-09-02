"""
ClaimGate — Stage D of Story Factory / Silent Auditor.

A flag may be "publishable" (not a fake vendor) and still fail ClaimGate
if it lacks actor + exact $ + contrast + receipt path.

SOT:
  data/content_truth_rules.yaml → publish_gate, forbidden_as_vendor_or_company
  data/silent_auditor_workflow.yaml → claim_gate_checklist
  docs/SILENT-AUDITOR-WORKFLOW.md Stage D
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
TRUTH_PATH = ROOT / "data" / "content_truth_rules.yaml"

_DOLLAR_RE = re.compile(
    r"\$\s*[\d,]+(?:\.\d+)?|\b[\d,]+\s*(?:million|billion|k)\b",
    re.I,
)
_REPORT_ID_RE = re.compile(
    r"\b(?:report\s*)?(?:#?\s*)?(\d{4,6}[A-Z]?)\b|"
    r"\b(\d{5}[IS])\b|"  # SBOA style 84477I / 82292S
    r"SBOA\s+([A-Z0-9\-]+)",
    re.I,
)
_PAGE_RE = re.compile(r"\bp(?:age)?\.?\s*(\d+)\b", re.I)
_PERSON_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)+)\b"
)
_CONTRAST_HINTS = (
    "median",
    "peer",
    "yoy",
    "year-over",
    "vs ",
    " versus ",
    "rate hike",
    "%",
    "percent",
    "county of",
    "population",
    "fixed income",
    "average",
    "typical",
)


@dataclass
class ClaimObject:
    """Structured claim ready for script / review card."""

    county: str = ""
    actor: str = ""
    actor_type: str = ""  # person | company | fund | place_utility | unknown
    exact_dollar: str = ""
    contrast: str = ""
    receipt_path: str = ""
    report_id: str = ""
    page: str = ""
    source_category: str = ""
    description: str = ""
    passes_gate: bool = False
    missing: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClaimGateResult:
    ok: bool
    claim: ClaimObject
    checklist: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "claim": self.claim.to_dict(),
            "checklist": self.checklist,
        }


def load_truth_rules() -> dict[str, Any]:
    if not TRUTH_PATH.is_file():
        return {}
    return yaml.safe_load(TRUTH_PATH.read_text(encoding="utf-8")) or {}


def _flag_text(f: Any) -> str:
    parts = [
        str(getattr(f, "description", "") or ""),
        str(getattr(f, "evidence", "") or ""),
        str(getattr(f, "recommended_action", "") or ""),
        str(getattr(f, "category", "") or ""),
    ]
    return " ".join(parts)


def _evidence_dict(f: Any) -> dict[str, Any]:
    raw = getattr(f, "evidence", None)
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _forbidden_vendor_set(rules: dict[str, Any]) -> set[str]:
    items = rules.get("forbidden_as_vendor_or_company") or []
    return {str(x).strip().lower() for x in items if x}


def _extract_dollar(text: str, ev: dict[str, Any]) -> str:
    for key in ("amount", "total", "compensation", "variance", "dollar"):
        if key in ev and ev[key] is not None:
            try:
                n = float(ev[key])
                if n >= 1:
                    return f"${n:,.0f}" if n >= 100 else f"${n:,.2f}"
            except (TypeError, ValueError):
                pass
    m = _DOLLAR_RE.search(text)
    return m.group(0).strip() if m else ""


def _extract_report_and_page(text: str, ev: dict[str, Any]) -> tuple[str, str]:
    rn = str(ev.get("report_number") or ev.get("report_id") or "").strip()
    page = str(ev.get("page") or "").strip()
    if not rn:
        m = _REPORT_ID_RE.search(text)
        if m:
            rn = next(g for g in m.groups() if g)
    if not page:
        m = _PAGE_RE.search(text)
        if m:
            page = m.group(1)
    return rn, page


def _extract_actor(f: Any, text: str, ev: dict[str, Any], forbidden: set[str]) -> tuple[str, str]:
    cat = (getattr(f, "category", "") or "").lower()
    for key in ("name", "employee", "official", "payee", "vendor", "fund", "entity", "line"):
        val = ev.get(key)
        if val and str(val).strip().lower() not in forbidden:
            actor = str(val).strip()
            if key in ("fund", "line"):
                return actor, "fund"
            if key in ("payee", "vendor"):
                return actor, "company"
            return actor, "person"

    # Salary-style "Last, First — Title"
    desc = getattr(f, "description", "") or ""
    m = re.match(r"^([A-Z][A-Za-z'.\-]+,\s+[A-Z][A-Za-z'.\-]+)", desc)
    if m:
        return m.group(1).strip(), "person"

    if cat in ("sboa_finding", "sboa_narrative"):
        # Prefer named person in excerpt; else place as fund/story actor later
        pm = _PERSON_RE.search(desc)
        if pm and len(pm.group(1).split()) >= 2:
            return pm.group(1).strip(), "person"

    if cat in ("dominant_disbursement", "budget_spike", "composition_outlier"):
        # Fund-style: quoted line name
        qm = re.search(r"['\"]([^'\"]{3,80})['\"]", desc)
        if qm and qm.group(1).strip().lower() not in forbidden:
            return qm.group(1).strip(), "fund"

    # Last resort: first Person-like token sequence not in forbidden
    for pm in _PERSON_RE.finditer(desc):
        cand = pm.group(1).strip()
        if cand.lower() not in forbidden and len(cand.split()) >= 2:
            return cand, "person"

    return "", "unknown"


def _extract_contrast(text: str, ev: dict[str, Any]) -> str:
    for key in ("contrast", "median", "peer", "yoy_pct", "rate_pct"):
        if ev.get(key):
            return str(ev[key])
    low = text.lower()
    for hint in _CONTRAST_HINTS:
        if hint in low:
            # capture a short window around first hint
            idx = low.find(hint)
            start = max(0, idx - 20)
            end = min(len(text), idx + 60)
            return text[start:end].strip()
    return ""


def _receipt_path(text: str, ev: dict[str, Any], report_id: str, page: str) -> str:
    url = ev.get("url") or ev.get("source_url") or ""
    if url:
        return str(url)
    src = ev.get("source") or ""
    if report_id:
        bits = [f"SBOA report {report_id}"]
        if page:
            bits.append(f"p.{page}")
        if src:
            bits.append(str(src))
        return " · ".join(bits)
    if "gateway" in text.lower() or "ifionline" in text.lower():
        return "gateway.ifionline.org (fund/year identity)"
    if "100r" in text.lower() or "employee compensation" in text.lower():
        return "Form 100R / Gateway Employee Compensation export"
    if src:
        return str(src)
    return ""


def evaluate_claim(f: Any, *, county: str = "") -> ClaimGateResult:
    """
    Run ClaimGate checklist on one red flag / finding-like object.

    Checklist (all required for ok=True):
      1. named actor (not forbidden rollup)
      2. exact dollar
      3. contrast metric identified
      4. receipt path (URL or report ID [+ page for SBOA])
    """
    rules = load_truth_rules()
    forbidden = _forbidden_vendor_set(rules)
    text = _flag_text(f)
    ev = _evidence_dict(f)
    cat = getattr(f, "category", "") or ""

    actor, actor_type = _extract_actor(f, text, ev, forbidden)
    if actor and actor.lower() in forbidden:
        actor, actor_type = "", "unknown"

    dollar = _extract_dollar(text, ev)
    contrast = _extract_contrast(text, ev)
    report_id, page = _extract_report_and_page(text, ev)
    receipt = _receipt_path(text, ev, report_id, page)

    # SBOA findings require report id (page preferred)
    is_sboa = "sboa" in cat.lower() or "sboa" in text.lower()
    if is_sboa and report_id and not receipt:
        receipt = f"SBOA report {report_id}" + (f" p.{page}" if page else "")

    missing: list[str] = []
    notes: list[str] = []

    has_actor = bool(actor and len(actor) >= 2)
    has_dollar = bool(dollar)
    has_contrast = bool(contrast)
    has_receipt = bool(receipt)
    if is_sboa and not report_id:
        has_receipt = False
        missing.append("report_id_and_page_when_sboa")

    if not has_actor:
        missing.append("named_actor")
    if not has_dollar:
        missing.append("exact_dollar")
    if not has_contrast:
        missing.append("contrast")
    if not has_receipt:
        missing.append("receipt_path")

    # Soft note: SBOA without page still can pass if report_id present (page preferred)
    if is_sboa and report_id and not page:
        notes.append("SBOA page number missing — preferred for watermark")

    checklist = {
        "exact_actor_spelling_100r_or_sboa": has_actor,
        "financial_variance_matches_report": has_dollar,
        "contrast_metric_identified": has_contrast,
        "report_id_and_page_logged": has_receipt
        if not is_sboa
        else bool(report_id),
    }

    ok = has_actor and has_dollar and has_contrast and has_receipt

    claim = ClaimObject(
        county=county or str(ev.get("county") or ""),
        actor=actor,
        actor_type=actor_type,
        exact_dollar=dollar,
        contrast=contrast,
        receipt_path=receipt,
        report_id=report_id,
        page=page,
        source_category=cat,
        description=(getattr(f, "description", "") or "")[:400],
        passes_gate=ok,
        missing=missing,
        notes=notes,
    )
    return ClaimGateResult(ok=ok, claim=claim, checklist=checklist)


def filter_flags_through_claim_gate(
    flags: list[Any],
    *,
    county: str = "",
    require_pass: bool = True,
) -> tuple[list[Any], list[ClaimGateResult]]:
    """Return flags that pass ClaimGate (or all with results if require_pass=False)."""
    kept: list[Any] = []
    results: list[ClaimGateResult] = []
    for f in flags:
        r = evaluate_claim(f, county=county)
        results.append(r)
        if r.ok or not require_pass:
            kept.append(f)
    return kept, results


def pick_best_claim_ready(
    flags: list[Any],
    *,
    county: str = "",
) -> tuple[Any | None, ClaimGateResult | None]:
    """
    Prefer ClaimGate-pass flags. Among passers, keep original order
    (caller should sort by hook rank first).
    """
    if not flags:
        return None, None
    results = [evaluate_claim(f, county=county) for f in flags]
    for f, r in zip(flags, results):
        if r.ok:
            return f, r
    # No passer — return best partial (fewest missing) for review card diagnostics
    best_i = min(range(len(results)), key=lambda i: len(results[i].claim.missing))
    return flags[best_i], results[best_i]


def claim_gate_summary(results: list[ClaimGateResult]) -> str:
    n_ok = sum(1 for r in results if r.ok)
    return f"ClaimGate: {n_ok}/{len(results)} flags pass (actor+$+contrast+receipt)"


if __name__ == "__main__":
    from core.handoff import RedFlag

    demo = RedFlag(
        severity="high",
        category="sboa_finding",
        description=(
            "SBOA 84477I p.12 (Clark): Unsupported disbursements of $128,400 "
            "cited for Clerk Jane Doe vs peer median salary contrast."
        ),
        evidence=json.dumps(
            {
                "report_number": "84477I",
                "page": 12,
                "amount": 128400,
                "source": "sboa",
                "url": "https://audit.sboa.in.gov/",
            }
        ),
    )
    r = evaluate_claim(demo, county="Clark")
    print(json.dumps(r.to_dict(), indent=2))
    print("PASS" if r.ok else "FAIL", r.claim.missing)

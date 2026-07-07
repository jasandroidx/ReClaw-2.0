"""
AuditCopilot — LLM narrative layer with statistical anchors (no raw ledger dump).

Feeds Ollama/local LLM:
  - RedFlag description + category
  - Global anchors (p50/p95/p99) for the county dataset
  - Algorithm scores (Isolation Forest, Benford MAD) when present

Returns structured JSON explanation for manifests, vault, and memory.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
import numpy as np

from core.config import get_settings
from core.handoff import RedFlag

OLLAMA_DEFAULT = "http://127.0.0.1:8080/api/generate"

SYSTEM_PROMPT = """You are a forensic analyst assistant for a public-records watchdog channel.
You receive ONLY pre-computed statistics and one flagged finding — never invent vendors or amounts.
Rules:
- Fair report: describe patterns; do not allege crimes or corruption.
- Cite only data provided in the user message.
- Return valid JSON only with keys: anomaly_flag (bool), confidence (0-1), explanation (string, max 120 words), features_cited (list of strings), recommended_public_question (string).
"""


def statistical_anchors(amounts: list[float]) -> dict[str, Any]:
    """Global statistical anchors for AuditCopilot prompts."""
    positives = [float(a) for a in amounts if a and float(a) > 0]
    if len(positives) < 5:
        return {"n": len(positives), "insufficient": True}
    arr = np.array(positives)
    return {
        "n": int(len(arr)),
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "insufficient": False,
    }


def _parse_evidence(evidence: str) -> dict:
    if (evidence or "").strip().startswith("{"):
        try:
            return json.loads(evidence)
        except Exception:
            pass
    return {"raw": (evidence or "")[:400]}


def _fallback_explanation(flag: RedFlag, anchors: dict[str, Any]) -> dict[str, Any]:
    ev = _parse_evidence(flag.evidence)
    amt = ev.get("amount") or ev.get("fence") or ev.get("mad")
    parts = [flag.description]
    if not anchors.get("insufficient") and amt:
        try:
            a = float(amt)
            if a >= anchors.get("p99", a):
                parts.append(f"Amount exceeds county p99 (${anchors['p99']:,.0f}).")
        except (TypeError, ValueError):
            pass
    return {
        "anomaly_flag": flag.severity in ("critical", "high"),
        "confidence": 0.72 if flag.severity == "high" else 0.55,
        "explanation": " ".join(parts)[:500],
        "features_cited": [flag.category, f"severity:{flag.severity}"],
        "recommended_public_question": flag.recommended_action
        or "Ask officials to explain this line at a public meeting with supporting invoices.",
        "source": "deterministic_fallback",
    }


def build_copilot_prompt(
    flag: RedFlag,
    *,
    county: str,
    anchors: dict[str, Any] | None = None,
    algorithm_scores: dict[str, Any] | None = None,
) -> str:
    ev = _parse_evidence(flag.evidence)
    return json.dumps(
        {
            "county": county,
            "flag": {
                "category": flag.category,
                "severity": flag.severity,
                "description": flag.description,
                "evidence_fields": ev,
                "recommended_action": flag.recommended_action,
            },
            "statistical_anchors": anchors or {},
            "algorithm_scores": algorithm_scores or {},
        },
        indent=2,
    )


def explain_flag(
    flag: RedFlag,
    *,
    county: str = "County",
    anchors: dict[str, Any] | None = None,
    algorithm_scores: dict[str, Any] | None = None,
    model: str | None = None,
    ollama_url: str | None = None,
    use_llm: bool | None = None,
) -> dict[str, Any]:
    """
    AuditCopilot explanation for one atomic finding.
    Falls back to deterministic template if Ollama unavailable.
    """
    settings = get_settings()
    if use_llm is None:
        use_llm = settings.enable_llm_analysis

    if not use_llm:
        out = _fallback_explanation(flag, anchors or {})
        out["county"] = county
        return out

    prompt = build_copilot_prompt(
        flag, county=county, anchors=anchors, algorithm_scores=algorithm_scores
    )
    url = ollama_url or OLLAMA_DEFAULT
    model = model or settings.llm_model

    try:
        r = httpx.post(
            url,
            json={
                "model": model,
                "prompt": f"{SYSTEM_PROMPT}\n\nDATA:\n{prompt}\n\nJSON:",
                "stream": False,
                "format": "json",
            },
            timeout=90.0,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Ollama HTTP {r.status_code}")
        raw = r.json().get("response", "")
        parsed = json.loads(raw) if raw.strip().startswith("{") else {}
        if not parsed.get("explanation"):
            raise ValueError("empty LLM explanation")
        parsed["source"] = "ollama_auditcopilot"
        parsed["county"] = county
        parsed["model"] = model
        return parsed
    except Exception as exc:
        out = _fallback_explanation(flag, anchors or {})
        out["county"] = county
        out["llm_error"] = str(exc)[:200]
        return out


def explain_top_flags(
    flags: list[RedFlag],
    *,
    county: str,
    amounts: list[float] | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Explain top severity flags with shared statistical anchors."""
    anchors = statistical_anchors(amounts or [])
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    ranked = sorted(flags, key=lambda f: order.get(f.severity, 9))[:limit]
    return [explain_flag(f, county=county, anchors=anchors) for f in ranked]


def county_disbursement_amounts(county: str, year: int = 2025) -> list[float]:
    try:
        from tools.split_purchase_detector import load_county_disbursements

        rows = load_county_disbursements(county, year)
        return [float(r["amount"]) for r in rows if float(r.get("amount") or 0) > 0]
    except Exception:
        return []
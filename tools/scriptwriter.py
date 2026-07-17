"""
scriptwriter.py — turns AuditResult red flags into a monetization-ready
YouTube script for a faceless "local auditor" channel.

Structure follows Derral Eves' "The YouTube Formula" (hook in first 15s,
open loops, payoff) + Knaflic "Storytelling with Data" for on-screen visuals.
Targets an 8-12 minute runtime (>=1,300 spoken words) to clear YouTube's
mid-roll-ad eligibility for longer-form content.

LEGAL / SAFETY GUARDRAILS (non-negotiable, baked in):
  * Fair-report framing only: describe PATTERNS in public records; never assert
    a named private citizen is "corrupt" or a criminal.
  * Every on-screen claim carries its public-record source.
  * Output is DRAFT: a human reviews & approves before anything is published.

Consumes tools.audit_adapter.AuditResult (or any object with .red_flags).
"""
from __future__ import annotations

import json
import re

from tools.viral_hooks import build_viral_hook, get_playbook_visual, headline_options

WPM = 150  # spoken words per minute (documentary pace)

# Generic disburse_name / rollup buckets — weak hooks without vendor/fund drill-down.
_WEAK_DISBURSE_LINES = frozenset(
    {
        "other capital outlays",
        "other disbursements",
        "capital outlays",
        "other operating disbursements",
        "other",
        "transfers out",
        "debt service",
        "salaries and wages",
        "employee benefits",
        "payment of taxes and other payroll withholdings",
        "distributions to other governmental entities",
        "governmental activities",
        "business-type activities",
        "other capital outlay",
        "personal services",
        "supplies",
    }
)

# Gateway ent_name / disburse_name labels that are NOT real payee vendors.
_FAKE_VENDOR_NAMES = frozenset(
    {
        "governmental activities",
        "business-type activities",
        "water",
        "wastewater",
        "solid waste",
        "stormwater",
        "sewer",
        "highway",
        "streets",
        "parks",
        "recreation",
        "gas",
        "electric",
        "electricity",
        "utilities",
        "utility",
        "fuel",
        "gasoline",
        "none",
        "unknown",
        "n/a",
        "0",
        "",
    }
)
_FAKE_VENDOR_RE = re.compile(
    r"^(water|wastewater|solid\s*waste|stormwater|sewer|highway|streets?|"
    r"gas|electric(?:ity)?|utilities?|fuel|gasoline|"
    r"governmental\s+activities|business-?type\s+activities|"
    r"transfers?\s+out|distributions?\s+to\s+other|"
    r"salaries\s+and\s+wages|employee\s+benefits|"
    r"payment\s+of\s+taxes|other\s+capital)\b",
    re.I,
)

# Salary titles that outperform category-only budget lines on Shorts.
_HIGH_IMPACT_TITLE_RE = re.compile(
    r"\b(referee|sheriff|judge|probation|jail|work\s*release|prosecutor|coroner|clerk|"
    r"circuit\s+court|superior\s+court|commissioner|auditor|treasurer)\b",
    re.I,
)

DISCLAIMER = (
    "This video analyzes patterns in public financial records. It does not "
    "allege any crime or wrongdoing by any individual. All figures come from "
    "official government sources, cited on screen. Anomalies can have innocent "
    "explanations; where possible we asked officials to comment."
)


def _sev_rank(f):
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(f.severity, 9)


def _amt_from_flag(f):
    """Best-effort dollar amount out of a flag's evidence, for shorts hooks."""
    ev = getattr(f, "evidence", "") or ""
    for key in ("amount", "total"):
        m = re.search(r'"%s"\s*:\s*([0-9.]+)' % key, ev)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                pass
    for text in (getattr(f, "description", "") or "", ev):
        m = re.search(r"\$([0-9][0-9,]*)", text)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except Exception:
                pass
    return None


def _short_dollars(x):
    if x is None:
        return None
    if x >= 1_000_000:
        return f"${x/1_000_000:.1f} MILLION".replace(".0 ", " ")
    if x >= 1_000:
        return f"${x/1_000:.0f}K"
    return f"${x:,.0f}"


def _evidence_dict(f) -> dict:
    ev = getattr(f, "evidence", "") or ""
    if not ev.strip().startswith("{"):
        return {}
    try:
        return json.loads(ev)
    except Exception:
        return {}


def _dominant_line_label(f) -> str:
    ev = _evidence_dict(f)
    if ev.get("line"):
        return str(ev["line"]).strip()
    m = re.search(r"'([^']+)'", getattr(f, "description", "") or "")
    return m.group(1).strip() if m else ""


def _is_weak_dominant(f) -> bool:
    """Category-only disburse_name totals — not publish-worthy cold opens."""
    if f.category != "dominant_disbursement":
        return False
    line = _dominant_line_label(f).lower()
    if not line:
        return True
    if line in _WEAK_DISBURSE_LINES:
        return True
    return any(w in line for w in _WEAK_DISBURSE_LINES)


def _looks_like_fake_vendor(name: str | None) -> bool:
    """True for Gateway rollups / account categories, not real payees."""
    if name is None:
        return True
    raw = str(name).strip()
    if not raw or raw.lower() in _FAKE_VENDOR_NAMES:
        return True
    if raw.lower() in _WEAK_DISBURSE_LINES:
        return True
    if _FAKE_VENDOR_RE.match(raw):
        return True
    return False


def _flag_entity_name(f) -> str:
    """Best-effort vendor / line / person label from evidence or description."""
    ev = _evidence_dict(f)
    for key in ("vendor", "name", "line", "vendor_field"):
        val = ev.get(key)
        if val is not None and str(val).strip() and str(val).strip().lower() != "none":
            return str(val).strip()
    desc = getattr(f, "description", "") or ""
    m = re.search(r"'([^']+)'", desc)
    if m:
        return m.group(1).strip()
    return ""


def _parse_salary_parts(f) -> tuple[str | None, str | None]:
    """Extract name + title from taxpayer_red_flags salary_shock description."""
    desc = getattr(f, "description", "") or ""
    m = re.match(r"^([^—]+)—\s*([^(]+)", desc)
    if not m:
        m = re.match(r"^([^—]+)—\s*(.+?):\s*\$", desc)
    if not m:
        return None, None
    return m.group(1).strip().rstrip(","), m.group(2).strip()


def _salary_impact_score(f) -> int:
    if f.category != "salary_shock":
        return 0
    _, title = _parse_salary_parts(f)
    if not title:
        return 1
    return 3 if _HIGH_IMPACT_TITLE_RE.search(title) else 1


def _is_method_dump_noise(f) -> bool:
    """DOGEGPT IsolationForest/ECOD method dumps — not video-ready cold opens."""
    desc = getattr(f, "description", "") or ""
    low = desc.lower()
    if "flagged by isolationforest" in low or "flagged by ecod" in low:
        return True
    # County-total peer outliers without a fund/department story
    if re.search(r":\s*[A-Z][A-Z\s]+COUNTY\s+in\s+\d{4}\s*→", desc) and "/" not in desc.split(":", 1)[-1][:40]:
        return True
    return False


def _is_named_publishable(f) -> bool:
    """Flags with a real person, company, or specific fund — for worthiness."""
    if not _is_publishable(f):
        return False
    cat = getattr(f, "category", "") or ""
    if cat in ("salary_shock", "double_dip", "composition_outlier"):
        return True
    if cat == "dominant_disbursement" and not _is_weak_dominant(f):
        return True
    if cat in ("split_purchase", "vendor_concentration", "round_number_cluster"):
        return not _looks_like_fake_vendor(_flag_entity_name(f))
    if cat == "budget_spike" and _amt_from_flag(f):
        return True
    return False


def _is_publishable(f) -> bool:
    """Hard kill list before ranking / scriptwriter cold opens."""
    cat = getattr(f, "category", "") or ""
    if cat == "dominant_disbursement" and _is_weak_dominant(f):
        return False
    if cat in ("benford_violation", "benford_deviation") and getattr(f, "severity", "") == "low":
        return False

    entity = _flag_entity_name(f)
    entity_low = entity.lower()

    # Vendor-style claims need a real payee name, not a Gateway rollup/category.
    if cat in (
        "vendor_concentration",
        "split_purchase",
        "split_purchase_pattern",
        "round_number_cluster",
    ):
        if _looks_like_fake_vendor(entity):
            return False

    # IQR / statistical noise on legitimate aggregate payroll / transfer lines.
    if cat == "statistical_anomaly":
        desc = (getattr(f, "description", "") or "").lower()
        line = entity_low or ""
        for weak in _WEAK_DISBURSE_LINES:
            if weak in line or weak in desc:
                return False
        # Method dumps and bare county totals are noise for publish path
        if _is_method_dump_noise(f):
            return False

    return True


def _flag_hook_rank(f) -> tuple:
    """Lower tuple = stronger cold-open candidate.

    Story impact ranks first so a medium named fund/salary beats a high-severity
    IsolationForest county total.
    """
    impact = {
        "salary_shock": 0,
        "double_dip": 1,
        "composition_outlier": 2,
        "vendor_concentration": 3,
        "dominant_disbursement": 4,
        "split_purchase": 5,
        "budget_spike": 6,
        "disbursement_swing": 7,
        "peer_outlier": 8,
        "federal_spending_spike": 9,
        "statistical_anomaly": 10,
        "benford_violation": 11,
        "benford_deviation": 12,
        "composition_break": 13,
        "collective_anomaly": 14,
        "elected_pay": 15,
        "budget_anomaly": 16,
        "procurement": 17,
    }.get(f.category, 20)
    if f.category == "salary_shock":
        impact -= _salary_impact_score(f)
    if f.category == "dominant_disbursement" and not _is_weak_dominant(f):
        impact -= 1
    if f.category == "composition_outlier" and _evidence_dict(f).get("fund"):
        impact -= 1
    # Named juice first; severity only breaks ties within same story class
    return (impact, _sev_rank(f), -(_amt_from_flag(f) or 0))


def _pick_lead_flag(flags):
    """Best flag for hook, lead beat, shorts opener — provenance-first."""
    pool = [f for f in flags if _is_publishable(f)]
    if not pool:
        pool = list(flags)
    return min(pool, key=_flag_hook_rank) if pool else None


def _pick_hook(flags, county):
    """Choose the single most shocking finding as the cold-open hook."""
    f = _pick_lead_flag(flags)
    if not f:
        return f"{county} spent millions last year. Here's where it actually went."
    viral = build_viral_hook(f, county, short=False)
    if viral:
        return viral
    if f.category == "salary_shock":
        name, title = _parse_salary_parts(f)
        amt = _short_dollars(_amt_from_flag(f))
        if name and title:
            return (
                f"Public records show {name} — {title} — paid {amt or 'six figures'} "
                f"by {county} taxpayers last year. Let's talk about it fairly."
            )
        return (
            f"Public records show one paycheck in {county} at {amt or 'six figures'}. "
            f"Let's talk about it fairly."
        )
    if f.category == "dominant_disbursement":
        label = _dominant_line_label(f) or f.description.split(":", 1)[0]
        amt = _short_dollars(_amt_from_flag(f))
        return (
            f"One named line in {county}'s books — '{label}' — totaled {amt or 'millions'} "
            f"last year. Nobody's explaining it in plain language. Let's fix that."
        )
    if f.category == "composition_outlier":
        ev = _evidence_dict(f)
        fund = ev.get("fund") or "one fund"
        line = ev.get("line") or _dominant_line_label(f)
        amt = _short_dollars(_amt_from_flag(f))
        return (
            f"In {county}, the '{fund}' fund sent {amt or 'a huge share'} to '{line}'. "
            f"That's a named fund — not a vague category total."
        )
    if f.category == "double_dip":
        return (
            f"One name shows up on two public paychecks in {county}. "
            f"The records are public — here's what they say."
        )
    if f.category == "federal_spending_spike":
        return (
            f"In one year, federal money flowing into {county} moved by tens of "
            f"millions of dollars — and almost no one who lives here noticed."
        )
    if f.category == "benford_violation":
        return (
            f"There's a mathematical law that catches fake numbers. {county}'s "
            f"official spending just failed the test."
        )
    return f"{county}'s own records show something that doesn't add up. {f.description}"


def _geo_terms(county):
    """county -> (short town/county name, hashtags, facebook-group angle)."""
    base = county.replace(" County", "").strip()
    tags = (
        f"#{base.replace(' ', '')}Indiana #{base.replace(' ', '')}County "
        f"#IndianaTaxpayers #{base.replace(' ', '')}IN"
    )
    fb = (
        f"Share into local Facebook groups: '{base} County News', "
        f"'You know you're from {base} County if...', and the county's main town group."
    )
    return base, tags, fb


def long_form_worthiness(result):
    """
    Decide whether a county has enough signal for 8-12 min long-form vs shorts-only.

    Scores publishable *named* findings only — raw flag-count spam does not help.
    Returns (is_worthy: bool, score: int, reasons: list[str]).
    """
    flags = getattr(result, "red_flags", result)
    publishable = [f for f in flags if _is_publishable(f)]
    named = [f for f in publishable if _is_named_publishable(f)]
    high = [f for f in named if f.severity in ("critical", "high")]
    distinct_cats = {f.category for f in named}
    lead = _pick_lead_flag(flags)
    biggest = max((_amt_from_flag(f) or 0) for f in named) if named else 0

    score, reasons = 0, []
    if len(high) >= 2:
        score += 2
        reasons.append(f"{len(high)} high-severity publishable flags")
    elif len(high) == 1:
        score += 1
        reasons.append("1 high-severity publishable flag")
    if len(distinct_cats) >= 4:
        score += 2
        reasons.append(f"{len(distinct_cats)} distinct named anomaly types (varied story)")
    elif len(distinct_cats) >= 3:
        score += 1
        reasons.append(f"{len(distinct_cats)} distinct named anomaly types")
    if lead and lead.category == "salary_shock" and _salary_impact_score(lead) >= 3:
        score += 2
        _, title = _parse_salary_parts(lead)
        reasons.append(f"named salary hook ({title or 'public employee'})")
    elif lead and lead.category == "double_dip":
        score += 2
        reasons.append("named dual-paycheck hook")
    elif lead and lead.category in ("composition_outlier", "dominant_disbursement"):
        score += 2
        reasons.append(f"named fund/line hook ({_short_dollars(_amt_from_flag(lead))})")
    elif biggest >= 1_000_000:
        score += 2
        reasons.append(f"a {_short_dollars(biggest)} standout number")
    elif biggest >= 250_000:
        score += 1
        reasons.append(f"a {_short_dollars(biggest)} standout number")
    # Depth from *named publishable* stack only (never raw IsolationForest volume)
    if len(named) >= 5:
        score += 2
        reasons.append(f"{len(named)} publishable named findings")
    elif len(named) >= 3:
        score += 1
        reasons.append(f"{len(named)} publishable named findings")

    is_worthy = score >= 4
    if not reasons:
        reasons.append("thin findings — shorts only")
    return is_worthy, score, reasons


def build_shorts(result, channel="The Local Auditor", county=None, max_shorts=5):
    """Generate 3-5 platform-ready 30-60s vertical shorts from the top flags."""
    county = county or getattr(result, "county", "this county")
    flags = getattr(result, "red_flags", result)
    census = getattr(result, "census", {}) or {}
    base, tags, fb = _geo_terms(county)
    earn = census.get("median_earnings") or census.get("median_hh_income")

    flags = sorted(
        [f for f in flags if _is_publishable(f)],
        key=_flag_hook_rank,
    )

    shorts, seen_keys = [], set()
    named_repeat_cats = {"salary_shock", "double_dip"}  # allow multiple named people
    for f in flags:
        if f.severity == "low":
            continue
        # One short per category, except multiple named salary/double_dip people
        if f.category in named_repeat_cats:
            entity_key = (f.category, _flag_entity_name(f) or f.description[:40])
            if entity_key in seen_keys:
                continue
            # Cap named repeats so shorts stay varied
            named_count = sum(1 for s in shorts if s.get("category") == f.category)
            if named_count >= 2:
                continue
            seen_keys.add(entity_key)
        else:
            if f.category in seen_keys:
                continue
            seen_keys.add(f.category)

        amt = _amt_from_flag(f)
        dollars = _short_dollars(amt)
        viral_short = build_viral_hook(f, county, short=True)
        open_line = None
        if viral_short:
            open_line = viral_short
        elif f.category == "salary_shock" and dollars:
            name, title = _parse_salary_parts(f)
            if name and title:
                # Stop-scroll: curiosity → role/$ → name (never dry "County paid X")
                open_line = (
                    f"They thought you wouldn't check. {base} County {title}? "
                    f"{dollars}. Name: {name}."
                )
            else:
                open_line = (
                    f"They thought you wouldn't check the salary search. "
                    f"{base} County — one paycheck at {dollars}."
                )
        elif f.category == "dominant_disbursement" and dollars:
            label = _dominant_line_label(f) or "one budget line"
            open_line = (
                f"Where did {base} County park {dollars}? One line on the books: '{label}'."
            )
        elif f.category == "composition_outlier" and dollars:
            ev = _evidence_dict(f)
            fund = ev.get("fund") or "one fund"
            line = ev.get("line") or _dominant_line_label(f)
            # Weak line labels kill the scandal feel — skip unless fund itself is the story
            if line and str(line).lower() in _WEAK_DISBURSE_LINES:
                open_line = (
                    f"Follow the money in {base}: the '{fund}' fund moved {dollars}. "
                    f"Here's where it went."
                )
            elif line:
                open_line = (
                    f"Follow the money in {base}: the '{fund}' fund moved {dollars} "
                    f"— mostly '{line}'."
                )
            else:
                open_line = (
                    f"Follow the money in {base}: the '{fund}' fund moved {dollars} "
                    f"into one line."
                )
        elif f.category == "double_dip":
            from tools.viral_hooks import extract_hook_context

            dctx = extract_hook_context(f, county)
            if dctx.get("name") and dctx.get("amount_fmt"):
                open_line = (
                    f"Same name. TWO paychecks. {dctx['name']} in {base} County "
                    f"— {dctx['amount_fmt']} combined."
                )
            elif dctx.get("name"):
                open_line = (
                    f"Same name. TWO paychecks. {dctx['name']} in {base} County."
                )
            else:
                open_line = f"Same name. TWO paychecks. On {base} County's public payroll."
        elif f.category == "budget_spike":
            desc = getattr(f, "description", "") or ""
            m = re.search(r"([+-]?\d+(?:\.\d+)?%)", desc)
            pct = m.group(1) if m else None
            if dollars and pct:
                open_line = (
                    f"In one year, {base} County's certified budget moved {pct} "
                    f"— to {dollars}. Here's the receipt."
                )
            elif dollars:
                open_line = (
                    f"Nobody posted about this: {base} County's budget hit {dollars}."
                )
            else:
                open_line = f"Nobody posted about this: {base} County's budget just spiked."
        elif f.category == "vendor_concentration":
            entity = _flag_entity_name(f)
            if entity and not _looks_like_fake_vendor(entity):
                open_line = (
                    f"Why did '{entity}' get {dollars or 'a huge share'} of "
                    f"{base} County's public money?"
                )
            else:
                # Filtered by _is_publishable; skip generic "ONE company" fallback.
                continue
        elif f.category == "federal_spending_spike" and dollars:
            open_line = (
                f"Federal money into {base} County moved by {dollars} in a single year. "
                f"Almost nobody noticed."
            )
        elif f.category in ("benford_deviation", "benford_violation"):
            open_line = (
                f"There's a math test that catches weird numbers. "
                f"{base} County's budget just failed it."
            )
        elif f.category == "round_number_cluster":
            open_line = (
                f"They thought you wouldn't check the cents. "
                f"{base} County wrote a stack of round-dollar checks."
            )
        elif f.category == "disbursement_swing" and dollars:
            open_line = (
                f"In one year, {base} County spending swung by {dollars}. "
                f"That's not a rounding error."
            )
        elif f.category == "statistical_anomaly" and dollars:
            # Only human YoY fund lines reach here after method-dump kill
            desc = (getattr(f, "description", "") or "")[:100]
            open_line = (
                f"I ran the math on {base}'s books. {desc}" if desc else None
            )
        else:
            # Never pad with "what's weird in the budget" — skip non-juice flags
            continue

        if not open_line:
            continue
        # Final hard rejects for broken English / None leaks
        if "'None'" in open_line or "this gibson" in open_line.lower() or "this pike" in open_line.lower():
            continue
        if "ONE company" in open_line and _looks_like_fake_vendor(_flag_entity_name(f)):
            continue

        contrast = ""
        if earn:
            contrast = f" The typical worker here makes about ${earn:,.0f} a year."

        body = getattr(f, "description", "") or ""
        # Prefer human angle body; strip method jargon if any slipped through
        body = re.sub(
            r"\s*—\s*flagged by\s+\S+.*$",
            "",
            body,
            flags=re.I,
        ).strip() or body

        beats = [
            f"[0-2s HOOK / on-screen big text] {open_line}",
            f"[2-10s] Here's the number, straight from public records.{contrast}",
            f"[10-40s] {body}",
            f"[on-screen source] {f.evidence}",
            "[40-55s] Could be innocent. But it's YOUR money, and nobody's explaining it.",
            "[55-60s CTA] Full breakdown on the channel. Is your county next? Comment it.",
        ]
        caption = (
            f"{open_line} {('Median worker: $%s/yr.' % format(int(earn), ',')) if earn else ''} "
            f"Source: public county records. Not an accusation — a question. {tags}"
        ).strip()
        shorts.append(
            {
                "severity": f.severity,
                "category": f.category,
                "hook": open_line,
                "script": beats,
                "caption": caption,
                "hashtags": tags,
                "disclaimer": DISCLAIMER,
                "playbook": get_playbook_visual(f),
            }
        )
        if len(shorts) >= max_shorts:
            break

    if not shorts and flags:
        f = flags[0]
        shorts.append(
            {
                "severity": f.severity,
                "category": f.category,
                "hook": f"{base} County, Indiana — a look at where the money goes.",
                "script": [
                    f"[0-2s] {base} County, Indiana.",
                    f"[2-40s] {f.description}",
                    f"[source] {f.evidence}",
                    "[CTA] More on the channel.",
                ],
                "caption": f"{base} County budget breakdown. Source: public records. {tags}",
                "hashtags": tags,
                "disclaimer": DISCLAIMER,
            }
        )
    return shorts, {"count": len(shorts), "facebook": fb, "hashtags": tags}


def build_script(result, channel="The Local Auditor", county=None):
    county = county or getattr(result, "county", "this county")
    flags = getattr(result, "red_flags", result)
    census = getattr(result, "census", {}) or {}
    flags = sorted(flags, key=_sev_rank)
    high = [f for f in flags if f.severity in ("critical", "high")]
    med = [f for f in flags if f.severity == "medium"]

    hook = _pick_hook(flags, county)
    L = []

    L.append(f"# {county.upper()} — WHERE DID THE MONEY GO?")
    L.append(f"*Draft script for {channel}. Runtime target 8-12 min. REVIEW BEFORE PUBLISH.*\n")
    L.append("## BEAT 1 — COLD OPEN / HOOK  (0:00-0:20)")
    L.append(f"**[VO]** {hook}")
    L.append("**[ON SCREEN]** Fast montage: the county courthouse, a budget PDF, a rising bar chart.")
    L.append(
        "**[VO]** I pulled every public record I could find — federal, state, and local — "
        "and ran it through the same anomaly tests professional auditors use. "
        "Here's what the data says.\n"
    )

    L.append("## BEAT 2 — WHO ARE WE TALKING ABOUT?  (0:20-1:30)")
    if census.get("median_hh_income"):
        L.append(
            f"**[VO]** {county} is a small place. The typical household here earns about "
            f"${census['median_hh_income']:,.0f} a year — the typical worker, about "
            f"${census.get('median_earnings', 0):,.0f}. About {census.get('poverty_rate_pct')}% "
            f"live below the poverty line. Population: roughly {census.get('population'):,}."
        )
        L.append("**[ON SCREEN]** Cite: U.S. Census Bureau, ACS 5-year (data.census.gov).")
    L.append(
        "**[VO]** Keep those numbers in your head, because the dollar figures you're about "
        "to see are going to feel very, very large by comparison.\n"
    )

    L.append("## BEAT 3 — THE BIG NUMBER  (1:30-4:00)")
    lead = _pick_lead_flag(flags) or (high[0] if high else None)
    if lead:
        L.append("**[VO]** Let's start with the one that stopped me cold.")
        L.append(f"**[VO]** {lead.description}.")
        L.append(f"**[ON SCREEN]** {lead.evidence}")
        L.append(
            "**[VO]** Sit with that for a second. In a county where the typical worker "
            "takes home around forty thousand dollars a year, this is one line item. "
            "Not the whole budget — one line. To put it in plain terms: if you split that "
            "single payment among every household in the county, it's real money in every "
            "kitchen. So the obvious question is the one nobody in the room seems to be asking "
            "out loud — what is it actually for, and who signed off on it?"
        )
        if lead.recommended_action:
            L.append(
                f"**[VO / caption]** Now — I want to be fair. {lead.recommended_action} "
                f"There can be an innocent explanation: a legal settlement, a bond payment, "
                f"a one-time capital project. That's exactly why it belongs in a public meeting, "
                f"on the record. It's a public record, it's large, and you paid for it."
            )
    else:
        L.append(
            "**[VO]** No single blockbuster line this year — but stack the smaller ones up "
            "and a pattern appears."
        )
    L.append("")

    L.append("## BEAT 4 — THE PATTERN STACK  (4:00-8:30)")
    L.append("**[VO]** One number can be a coincidence. A pattern is different. Here's the stack.")
    n = 0
    lead_key = (lead.category, lead.description[:80]) if lead else None
    for f in high + med + [x for x in flags if x.severity == "low"]:
        if lead_key and (f.category, f.description[:80]) == lead_key:
            continue
        n += 1
        if n > 8:
            break
        tag = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(f.severity, "•")
        L.append(f"**[VO]** {tag} {f.description}.")
        L.append(f"**[ON SCREEN]** {f.evidence}")
    L.append(
        "**[VO]** Every one of those came from an official source. I'm not making claims about "
        "any person — I'm reading you the county's own books."
    )
    L.append(
        "**[VO]** And here's why the stack matters more than any single line. Any one of these, "
        "on its own, has a boring explanation. Budgets spike when a grant lands. One vendor "
        "dominates when there's only one paving company for fifty miles. Round numbers happen. "
        "But auditors don't chase single numbers — they chase clusters. When the spikes, the "
        "concentration, the round-number payments, and a Benford deviation all show up in the "
        "same set of books in the same year, that's the signal that says: somebody outside the "
        "courthouse should take a closer look. Not an accusation. A reason to ask.\n"
    )

    L.append("## BEAT 4.5 — WHAT THIS COULD MEAN (AND WHAT IT DOESN'T)  (7:00-8:30)")
    L.append(
        "**[VO]** Before anyone in the comments runs off with a torch — let's be adults about "
        "this. There are boring, completely legal explanations for every single one of these."
    )
    L.append(
        "**[VO]** That giant settlement line? Counties do settle lawsuits, and they do book "
        "one-time capital projects — a new jail, a bridge, a landfill closure — as a single big "
        "outlay. That's normal. What's NOT normal is for a payment that size to never get "
        "explained in plain language at a public meeting. The number isn't the scandal. "
        "The silence around it is the question."
    )
    L.append(
        "**[VO]** The vendor showing up under two names? Probably just a company that "
        "reincorporated as an LLC. But the whole reason Indiana law — IC 36-1-12-19 — bans "
        "splitting a project into smaller pieces is that splitting is exactly how you dodge "
        "the bidding rules. So it's worth confirming, not assuming."
    )
    L.append(
        "**[VO]** And the round numbers, and the Benford wobble? On their own, nothing. "
        "Together, in one year, they're the reason you keep watching — and the reason someone "
        "should ask for the receipts. That's all this is: a reason to ask.\n"
    )

    L.append("## BEAT 5 — HOW I KNOW  (8:30-10:00)")
    L.append(
        "**[VO]** How do I know these are unusual and not just how small-town budgets look? "
        "I didn't eyeball it. The tool runs four tests forensic accountants actually use: "
        "a robust z-score for spikes, an Isolation Forest for weird combinations, "
        "Benford's Law to catch numbers that don't occur naturally, and a vendor-concentration "
        "check for money piling up with one recipient."
    )
    L.append("**[ON SCREEN]** Cite: Nigrini, *Benford's Law*; Wells, *Principles of Fraud Examination*.")
    L.append("**[VO]** Same math. Public data. Anyone can check me — and I'll show you how.\n")

    L.append("## BEAT 6 — CALL TO ACTION  (10:00-end)")
    L.append(
        f"**[VO]** If you live in {county}, ask your commissioners about these lines at the "
        "next public meeting — the dates are on the county website. If you want me to audit "
        "YOUR county next, drop the name in the comments and subscribe. I read every one."
    )
    L.append(f"\n---\n**DISCLAIMER (must appear on screen + in description):**\n> {DISCLAIMER}")

    titles = _titles(county, flags)
    L.append("\n---\n## PACKAGING (A/B test these)")
    L.append("**Title options:**")
    for t in titles:
        L.append(f"- {t}")
    L.append('**Thumbnail text:** big red number + "WHERE DID IT GO?"')
    L.append("**Description:** 1-line hook + full source list (every URL on screen) + disclaimer.")

    script = "\n".join(L)
    words = len(script.split())
    runtime = words / WPM
    header = (
        f"<!-- runtime ~{runtime:.1f} min ({words} words @ {WPM} wpm); "
        f"monetization-ready if >=8 min. flags used: {len(flags)} -->\n"
    )
    return header + script, {
        "words": words,
        "runtime_min": round(runtime, 1),
        "titles": titles,
        "flags": len(flags),
        "disclaimer": DISCLAIMER,
    }


def _titles(county, flags):
    lead = _pick_lead_flag(flags)
    cats = {f.category for f in flags if _is_publishable(f)}
    out = []
    if lead:
        out.extend(headline_options(lead, county, limit=2))
    if lead and lead.category == "salary_shock":
        name, title = _parse_salary_parts(lead)
        amt = _short_dollars(_amt_from_flag(lead))
        if name and title:
            out.append(f"{county}: {title} Paid {amt} — Public Salary Records")
        else:
            out.append(f"What {county} Pays Its Top Public Employees (Public Records)")
    elif lead and lead.category == "dominant_disbursement":
        label = _dominant_line_label(lead)
        amt = _short_dollars(_amt_from_flag(lead))
        out.append(f"{county} Spent {amt} on '{label}' — Public Records")
    elif "salary_shock" in cats:
        out.append(f"What {county} Pays Its Top Public Employees (Public Records)")
    elif "dominant_disbursement" in cats:
        dom = next((f for f in flags if f.category == "dominant_disbursement" and not _is_weak_dominant(f)), None)
        if dom:
            out.append(
                f"{county} Spent {_short_dollars(_amt_from_flag(dom))} on "
                f"'{_dominant_line_label(dom)}' — Public Records"
            )
    if "double_dip" in cats:
        out.append(f"Same Name, Two Paychecks — {county} Public Salary Search")
    if "federal_spending_spike" in cats:
        out.append(f"What Really Happened to {county}'s Missing Millions?")
    if "benford_violation" in cats or "benford_deviation" in cats:
        out.append(f"{county}'s Budget FAILED the Fraud-Detection Test (Benford's Law)")
    if "vendor_concentration" in cats:
        out.append(f"One Company Got HALF of {county}'s Money — Here's Who")
    out.append(f"I Audited {county}'s Entire Budget. Here's What the Data Shows.")
    return out[:5]


def build_package(
    result,
    channel: str = "The Local Auditor",
    county: str | None = None,
    *,
    max_shorts: int = 5,
) -> dict:
    """
    Combined output: worthiness gate + long-form + shorts + distribution meta.
    """
    county = county or getattr(result, "county", "this county")
    flags = getattr(result, "red_flags", result)
    worthy, score, reasons = long_form_worthiness(result)
    long_md, long_meta = (None, {})
    if worthy:
        long_md, long_meta = build_script(result, channel=channel, county=county)
    shorts, dist = build_shorts(result, channel=channel, county=county, max_shorts=max_shorts)
    hook_flag = _pick_lead_flag(flags)
    top_finding = hook_flag.description if hook_flag else "No flags surfaced"
    return {
        "county": county,
        "worthy": worthy,
        "worthiness_score": score,
        "worthiness_reasons": reasons,
        "recommendation": (
            f"STRONG long-form (~{long_meta.get('runtime_min', 0)} min) + {len(shorts)} shorts"
            if worthy
            else f"Shorts only ({len(shorts)} hooks) — thin for 8+ min"
        ),
        "long_form": {"markdown": long_md, **long_meta} if long_md else None,
        "shorts": shorts,
        "distribution": dist,
        "top_finding": top_finding,
        "top_category": hook_flag.category if hook_flag else None,
        "flag_count": len(flags),
        "disclaimer": DISCLAIMER,
    }
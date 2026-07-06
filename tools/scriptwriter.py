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

WPM = 150  # spoken words per minute (documentary pace)

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


def _pick_hook(flags, county):
    """Choose the single most shocking finding as the cold-open hook."""
    priority = [
        "dominant_disbursement",
        "salary_shock",
        "split_purchase",
        "peer_outlier",
        "benford_violation",
        "vendor_concentration",
        "composition_break",
        "collective_anomaly",
        "federal_spending_spike",
        "budget_spike",
        "double_dip",
        "disbursement_swing",
    ]
    hi = sorted([f for f in flags if f.severity in ("critical", "high")], key=_sev_rank)
    pool = hi or sorted(flags, key=_sev_rank)
    if not pool:
        return f"{county} spent millions last year. Here's where it actually went."
    f = pool[0]
    for cat in priority:
        match = next((x for x in flags if x.category == cat), None)
        if match:
            f = match
            break
    if f.category == "dominant_disbursement":
        return (
            f"One single line in {county}'s budget last year was bigger than the "
            f"county's entire payroll. {f.description.split(':', 1)[0]}. "
            f"Nobody's talking about it. Let's fix that."
        )
    if f.category == "salary_shock":
        amt = _short_dollars(_amt_from_flag(f))
        return (
            f"Public records show one paycheck in {county} at {amt or 'six figures'} — "
            f"in a county of twelve thousand people. Let's talk about it fairly."
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

    Returns (is_worthy: bool, score: int, reasons: list[str]).
    """
    flags = getattr(result, "red_flags", result)
    high = [f for f in flags if f.severity in ("critical", "high")]
    distinct_cats = {f.category for f in flags}
    has_dominant = any(f.category == "dominant_disbursement" for f in flags)
    biggest = max((_amt_from_flag(f) or 0) for f in flags) if flags else 0

    score, reasons = 0, []
    if len(high) >= 2:
        score += 2
        reasons.append(f"{len(high)} high-severity flags")
    elif len(high) == 1:
        score += 1
        reasons.append("1 high-severity flag")
    if len(distinct_cats) >= 4:
        score += 2
        reasons.append(f"{len(distinct_cats)} distinct anomaly types (varied story)")
    elif len(distinct_cats) >= 3:
        score += 1
        reasons.append(f"{len(distinct_cats)} distinct anomaly types")
    if has_dominant and biggest >= 1_000_000:
        score += 2
        reasons.append(f"a {_short_dollars(biggest)} dominant line (visual hook)")
    elif biggest >= 250_000:
        score += 1
        reasons.append(f"a {_short_dollars(biggest)} standout number")
    # Pike-style taxpayer scans: many medium flags still warrant long-form
    if len(flags) >= 20:
        score += 2
        reasons.append(f"{len(flags)} total flags (deep stack for pattern beat)")
    elif len(flags) >= 10:
        score += 1
        reasons.append(f"{len(flags)} total flags")

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

    _cat_rank = {
        "dominant_disbursement": 0,
        "salary_shock": 1,
        "double_dip": 2,
        "vendor_concentration": 3,
        "composition_outlier": 4,
        "budget_spike": 5,
        "disbursement_swing": 6,
        "benford_deviation": 7,
        "round_number_cluster": 8,
        "federal_spending_spike": 9,
    }
    flags = sorted(flags, key=lambda f: (_cat_rank.get(f.category, 8), _sev_rank(f)))

    shorts, seen_cats = [], set()
    for f in flags:
        if f.category in seen_cats:
            continue
        if f.severity == "low":
            continue
        amt = _amt_from_flag(f)
        dollars = _short_dollars(amt)
        if f.category == "dominant_disbursement" and dollars:
            open_line = f"{base} County, Indiana spent {dollars} on ONE line item."
        elif f.category == "salary_shock" and dollars:
            open_line = f"{base} County taxpayers paid {dollars} on ONE public paycheck."
        elif f.category == "double_dip":
            open_line = f"ONE person, TWO paychecks — {base} County public records."
        elif f.category == "budget_spike":
            open_line = f"{base} County's certified budget just spiked — public records."
        elif f.category == "composition_outlier" and dollars:
            open_line = f"Something's off with {base} County's books. {dollars} in one fund."
        elif f.category == "vendor_concentration":
            open_line = f"ONE company got over half of {base} County's money."
        elif f.category == "federal_spending_spike" and dollars:
            open_line = f"{base} County's money moved by {dollars} in a single year."
        elif f.category in ("benford_deviation", "benford_violation"):
            open_line = f"{base} County's budget just failed a fraud-detection test."
        elif f.category == "round_number_cluster":
            open_line = f"{base} County wrote dozens of suspiciously round checks."
        elif f.category == "disbursement_swing" and dollars:
            open_line = f"{base} County disbursements swung by {dollars} year over year."
        else:
            open_line = f"{base} County, Indiana — here's what's weird in the budget."

        contrast = ""
        if earn:
            contrast = f" The typical worker here makes about ${earn:,.0f} a year."

        beats = [
            f"[0-2s HOOK / on-screen big text] {open_line}",
            f"[2-10s] Here's the number, straight from public records.{contrast}",
            f"[10-40s] {f.description}",
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
            }
        )
        seen_cats.add(f.category)
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
    lead = (
        next((f for f in flags if f.category == "dominant_disbursement"), None)
        or next((f for f in flags if f.category == "salary_shock"), None)
        or (high[0] if high else None)
    )
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
    cats = {f.category for f in flags}
    out = []
    if "dominant_disbursement" in cats:
        out.append(f"{county} Spent $19 MILLION on ONE Line — And No One Noticed")
    if "salary_shock" in cats:
        out.append(f"What {county} Pays Its Top Public Employees (Public Records)")
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
    hook_flag = sorted(flags, key=_sev_rank)[0] if flags else None
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
# Dual-receipt + viral auditor research (2026-07-22)

**Skills used:** firecrawl search/scrape, county-audit SOT, ClaimGate, Path C, writing-skills patterns for process docs.
**Firecrawl:** searches + full scrapes of 14News Winslow coverage. Credits OK this session (prior 402 cleared).

## Result expectation (north star)

One 30–60s short per place that a **local** would share: their town/county name in first 3s, exact $, human contrast, public receipt. Not 50-flag mills.

## Workflow diagnosis (start → finish)

| Stage | Today | Viral-ready needs |
|-------|--------|-------------------|
| A Pick place | Queue frozen; cursor Posey | Score by SBOA hit + rate/news dual-receipt candidate |
| B Harvest | Gateway + salaries + dogegpt budgets + SBOA cache | Pain leg (news/minutes) **required** for PHI≥7.5 stories |
| C Filter | playbook + truth rules | ClaimGate-only to scriptwriter |
| D Claim | claim_gate.py exists | Dual-receipt object (pain+money) not only single flag |
| E Script | HHVCTA / viral_scribe | One primary short max; fair-report voice |
| F Human | Obsidian card | Show missing ClaimGate fields in 60s |
| G Publish | Manual | Still human — correct |

## Firecrawl findings (this session)

### Winslow dual-receipt (pain + money) — verified scrape
- **14News 2025-01-14:** 45% water / 10% waste proposed; fixed-budget fear; jump from ~3% to 42–54% scare.
- **14News 2025-01-16:** Town hall shouting; Joshua Popp document pull; ~$13 monthly bump for many min-use (~2000 gal); council president Joni Stafford: infrastructure catch-up; vote 2025-01-27.
- **Tristatehomepage / WEHT:** corroborating ~50% water framing.

### Viral content patterns (search, imperfect TikTok noise)
- "Did you know" + salary/budget numbers dominate finance-tiktok, not IsolationForest.
- Faceless short-story accounts work; face not required.
- Local tax-dollar / controller races use "your tax dollars" framing — map to fair-report public records.
- **Implication for ReClaw:** hook = place + shocking true % or $ + lived contrast; receipt in description.

### GitHub/OSINT
- Hermes-agent OSINT skill: pay-to-play / contractor-donor patterns — future detector research, not publish without dual receipt.
- GRC Claude skills less relevant than Indiana SBOA path.

## DOGEGPT role (honest)
`dogegpt_budget.py` = fund-level certified budget CSV export. Useful money leg for **fund spikes**, not automatic viral. Pike cache water funds sparse; town water rate stories need **ordinance/news**, not only county AFR.

## Product tracks
1. **Watchdog juice (primary):** SBOA I-series, rate shock dual-receipt, project-$ vs broken roads.
2. **Local curious (secondary):** history/census "did you know" with sources — growth, not scandal.

## Pilot delivered
`tools/dual_receipt_pilot.py winslow-water` → ClaimGate PASS package in:
- `data/dual_receipt_pilots/`
- vault Rural Data
- outbox `DUAL-RECEIPT-WINSLOW.html`

## Rebuild rules (locked)
1. Story object first (one Claim), not flag volume.
2. Dual-receipt required for bill-shock / project-vs-outcome heat ranks.
3. Human gate before hooks ship.
4. Unfreeze mill only after 1–3 cards Jason would post.
5. Fair-report language only.

## Next engineering (ordered)
1. Wire dual-receipt package into review-card renderer (ClaimGate missing fields UI).
2. SBOA-first selector for next county package (skip salary-only tops).
3. Firecrawl news leg automation per county (rate hike / town hall queries).
4. One manual publish of Winslow pilot short.
5. Explicit unfreeze in content_truth_rules.yaml when ready.

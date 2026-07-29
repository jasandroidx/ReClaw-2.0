---
name: indiana-rural-grants
description: |
  Research and draft Indiana-relevant rural agriculture grant shortlists
  (beekeeping, greenhouse, specialty crops, conservation, small farm).
  Uses Grants.gov search2 (no API key) + ISDA program pages + Firecrawl for NOFOs.
  Triggers: grant digest, rural grants, SCBG, RFSI, REAP, beekeeping grant,
  greenhouse funding, Indiana farm grant, Grant Hall, Scribe Warden.
  Never auto-applies. Human gate before email/send/portal submit.
---

# Indiana rural grants

Produce a **human-reviewed** shortlist of public funding opportunities relevant to rural Indiana operators. Prefer truth + provenance over volume.

## Hard gates

- **Never** submit applications, portal forms, or mass emails.
- **Never** invent eligibility, award amounts, or deadlines.
- Every row must have a **source URL** the human can open.
- Output is always **draft** until Jason (or operator) checks the checklist.
- County content queue stays independent — do not unfreeze Posey / run-next from this skill.

## Quick start (this host)

```bash
cd /root/ReClaw-2.0
PYTHONPATH=. .venv/bin/python scripts/grant_digest_thin.py \
  --query "beekeeping greenhouse specialty crop rural Indiana" --limit 8
```

Or:

```bash
bash /root/.openclaw/workspace/skills/indiana-rural-grants/scripts/run_digest.sh \
  "beekeeping greenhouse specialty crop" 8
```

Draft lands in `/root/ReClaw-2.0/data/grant_digests/`. Copy polished version to Ravenstack `ops/` only with explicit intent.

## Workflow

1. **Search public sources**
   - Grants.gov `POST https://api.grants.gov/v1/api/search2` (no auth) — see [references/grants-gov-search2.md](references/grants-gov-search2.md)
   - ISDA grants hub + program pages — see [references/indiana-isda-sources.md](references/indiana-isda-sources.md)
   - Optional: Firecrawl scrape NOFO PDFs / ISDA pages for deadlines and eligibility
2. **Score & prune** using [references/scoring-rubric.md](references/scoring-rubric.md). Drop low rural-IN fit.
3. **Render digest** — table: program | agency | deadline | link | why rural IN
4. **Human checklist** — verify each link/deadline before any send
5. **Optional** — emit Grant Hall visual note / vault pending_approval (MCP write only if operator asked)

## Recommended queries (rotate)

| Theme | Example keyword |
|-------|-----------------|
| Specialty crops / greenhouse | `specialty crop Indiana` / `horticulture greenhouse` |
| Beekeeping / pollinators | `honey bee pollinator` |
| Conservation / water | `rural conservation Indiana` / `water quality agriculture` |
| Energy / REAP-style | `rural energy agriculture renewable` |
| Beginning / small farm | `beginning farmer` / `value added producer` |

Run 1–3 focused queries rather than one giant dump. Cap digest at **5–10 rows**.

## Output template

```markdown
# Indiana rural grant shortlist — week of YYYY-MM-DD

_Draft only. Human must verify every link and deadline before sending._

| # | Program | Agency | Deadline | Link | Why care |
|---|---------|--------|----------|------|----------|
| 1 | ... | ... | ... | https://... | ... |

## Human checklist before send
- [ ] Every deadline checked on source page
- [ ] Eligibility matches recipient type (nonprofit / farm / local gov)
- [ ] No invented award sizes
- [ ] Disclaimer: not legal/financial advice

## Sources
- Grants.gov search2
- ISDA program pages (list URLs)
```

## Pricing / product notes (operator)

Path-C side offer: free 2-week pilot → **$49/mo** shortlist for nonprofits / towns / rural biz. Agent prepares; human sells and sends.

## Related fortress pieces

- SOUL: `agents/grant_watcher/SOUL.md`
- Script: `scripts/grant_digest_thin.py`
- Room: Grant Hall (dashboard) — Scribe Warden
- Plan: `docs/operator/PATH-C-DUAL-INCOME-2026-07-17.md`

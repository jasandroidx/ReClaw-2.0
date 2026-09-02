# SYSTEM DIRECTIVE: Silent Auditor Workflow for OpenClaw Agents

**Version:** 2.0 — Comprehensive (merged operator V1 + V2 + ReClaw wiring)  
**Status:** **ACTIVE SOT** for Silent Auditor media operations  
**Updated:** 2026-07-17  
**Vault twin:** `Ravenstack/ops/SILENT-AUDITOR-WORKFLOW.md`  
**Machine rules:** `data/silent_auditor_workflow.yaml`  
**Related:** `docs/CONTINUOUS-IMPROVEMENT.md` · `data/content_truth_rules.yaml` · `data/indiana_public_finance_blueprint.yaml`

> **Not legal advice.** Legal modules summarize operational constraints distilled from Indiana public-records / fair-report research for agent behavior. When in doubt, human counsel + final filed documents only.

---

## Core objective

Convert complex **Indiana municipal finance records** into **verified, compelling short-form video scripts** without:

1. Defamation liability (fair report only; no criminal imputation without charges)  
2. Violating SBOA draft confidentiality  
3. Violating public-records access norms (APRA / rate limits)  
4. Publishing **fake vendors** from Gateway fund rollups  

**Operational philosophy**

| Do | Don’t |
|----|--------|
| Deterministic, rule-based heuristics | IsolationForest / ECOD / unsupervised ML as **publishable** anomaly stories |
| Final, filed official documents only | Draft / exit-conference / unfiled audits |
| Named actor + exact $ + contrast + receipt | Category totals as “ONE company” scandals |
| One story with Public Heat Index priority | Sixty-flag mills and method-name cold opens |

---

## MODULE 1 — Legal firewalls & defamation prevention

### 1.1 Fair Report Privilege (primary shield)

- Publish a **fair, accurate, unbiased** abridgement of an **official government document or proceeding**.  
- Capture the **gist and sting** of the official record; do not mislead about what the record says.  
- **Always attribute:** e.g. *“According to the Indiana State Board of Accounts…”*  
- **Only extract from final, officially filed documents.**

### 1.2 SBOA draft confidentiality (hard stop)

- Under research mapping to **IC 5-11-5-1**: preliminary audit reports, draft comments, and exit-conference discussions are **confidential until the final report is filed**.  
- Agents must **never** ingest, analyze, or publish draft/unfiled/leaked preliminary findings.  
- **Only** final WebReports filings (and other final public records).  
- Tooling: `tools/sboa_ingest.py` uses the public filings API — treat only filed reports in cache as publishable.

### 1.3 Substantial truth & language (defamation per se)

| Allowed (objective / SBOA-style) | Forbidden (unless quoting a formal charge sheet) |
|----------------------------------|--------------------------------------------------|
| requested reimbursement | stole |
| unaccounted for | embezzled |
| personal obligation (as SBOA phrases it) | corrupt / fraud / theft (as allegation) |
| misappropriated / diverted **only if the final report uses that language** | inventing criminal intent |

- Minor clerical slips may be protected if the **gist** matches the record; **never invent** dollars or actors.  
- Prefer exact report language over paraphrase when stakes are high.

### 1.4 Public records / APRA / scraping

- Agencies may block aggressive automated scraping if it burdens systems or is treated as a security risk.  
- **Human-gated, low-frequency** pipelines preferred.  
- Prefer bulk/official downloads and off-peak windows; random delays for browser automation.  
- APRA drafts (when needed) must have **reasonable particularity**: dates, funds, vendors, report IDs.  
- Social media comments are **leads only** — never facts.

---

## MODULE 2 — Source priority & data structures

Agents query sources in this order. Map to ReClaw tools/paths.

| Priority | Source | What to take | Never use for | ReClaw path |
|----------|--------|--------------|---------------|-------------|
| **1 (highest)** | SBOA WebReports — **Special Investigation** / files ending in **`I`** / `I.pdf` | Named $ variance, responsible officials, special investigation costs, page + report ID | Draft text | `tools/sboa_ingest.py` → `data/cache/sboa/{county}/` |
| **2** | Gateway **Form 100R** | Names, titles, total compensation; dual lines; nepotism/contracting policy answers (when present) | Cross-county salary bleed | `data/cache/salaries/salary_{gateway_code}_{year}.csv` · export scripts |
| **3** | Gateway **township** “Disbursements by Vendor” | Annual cumulative payee totals (no payment dates) | Treating as same-day AP register | County-specific township CSVs when available |
| **4** | **IURC** dockets | Base rate increases, infrastructure surcharges | Vendor fraud claims | Manual / Firecrawl discovery → inbox |
| **5** | County **AP registers / claims dockets** | Split-purchase, named payees, board-approved claims | Inventing payees from AFR | `data/inbox/` + `tools/transaction_anomaly.py` |
| **Supporting** | Gateway **AFR** / certified budgets | Fund YoY, fiscal stress ratios | **Vendor payee** drama | Gateway cache · `tools/fiscal_health.py` |

### Critical structural difference (Gateway AFR)

| Unit type | Vendor visibility on public AFR |
|-----------|----------------------------------|
| **Townships** | Often have “Disbursements by Vendor” (annual totals per payee) |
| **Counties / cities** | **Do not** list individual vendors on public AFR |

**County AFR `ent_name` / `disburse_name` is NOT a private company.**  
Examples that are **never vendors**: Governmental Activities, WATER, GAS, Salaries and Wages, Transfers Out, Other Capital Outlays.

Deadlines (for late-filing heuristics, not criminal stories):

- Form 100R: typically **Jan 31**  
- AFR: typically **Mar 1** (60 days after fiscal year close) — research-derived; confirm against current DLGF/Gateway guidance when scoring.

---

## MODULE 3 — Anomaly detection (heuristic triggers only)

**Do not use unsupervised ML models as the story engine.**  
IsolationForest / ECOD may exist in research/lab layers for exploration; they **must not** produce IsolationForest-named cold opens or dominate risk scores for publish.

### Prefer these triggers

1. **Unsupported disbursements** (SBOA narrative: missing receipts/invoices/tickets; personal obligation language when in the report)  
2. **Internal control deficiencies** (no monthly bank recon; segregation of duties — as stated in final report)  
3. **Personal / luxury / unsupported personal use of public funds** (only as documented in final SBOA special investigation)  
4. **Late filings** vs statutory deadlines (compliance story, not theft story)  
5. **Dual compensation lines** same name (Form 100R) above playbook thresholds  
6. **Named salary contrast** with peer/median (supporting cast — not the whole channel)  
7. **Utility rate / bill shock** (IURC + local ordinance + news for pain leg)  
8. **True vendor patterns** only from **claims dockets / township vendor CSV / SBOA-named payee**

### Filter cleaning (Stage B rules)

- Strip AFR internal fund transfers and rollups (Governmental Activities, etc.).  
- Filter Form 100R noise: low-dollar seasonal (e.g. under **$15,000** as supporting only; do not lead with lifeguard-tier pay).  
- Drop standard municipal software providers as “scandal” unless SBOA names them.  
- **ML theater deflater:** drop any candidate without an **explicit named actor** and a **specific dollar variance**.

### Public Heat Index (PHI) — Stage C

```
PHI = 0.40(Severity) + 0.30(Clarity) + 0.20(Contrast) + 0.10(Relevance)
```

- Prefer **filed SBOA Special Investigation** charges first.  
- Operational target: select the **single best story** with PHI **≥ 7.5** when available; otherwise the best dual-receipt candidate, not flag volume.  
- Aligns with heat_rank in `content_truth_rules.yaml` (SBOA → bill shock → project vs outcome → … → salary supporting).

---

## MODULE 4 — Pipeline stages A–H (execution map)

### Stage A — Intake

| Input | Tool / path |
|-------|-------------|
| SBOA I.pdf / special investigations | `./scripts/run_sboa_discovery.sh {County}` · `tools/sboa_ingest.py` |
| Form 100R bulk | `scripts/export_county_salaries.py` |
| Township vendor / AP CSVs | drop in `data/inbox/` |
| Heat leads (Reddit/FB) | `data/inbox/heat/` — leads only |

Respect rate limits; human gate for aggressive browser harvests.

### Stage B — Filter cleaning

- `tools/auditor_playbook.filter_flags_by_truth`  
- RULEBOOK disabled procurement-on-Gateway  
- scriptwriter `_is_publishable` / rollup kill lists  

### Stage C — Story selection

- Prefer SBOA flags + dual-receipt templates over detector volume  
- PHI / heat_rank ordering  
- Continuous improve: open mistakes in `audit_pipeline_mistakes.yaml`

### Stage D — Claim object validation (ClaimGate checklist)

Before any short is “ready”:

1. Exact actor spelling vs Form 100R or SBOA named official  
2. Dollar variance matches report to the **exact amount stated**  
3. Contrast metric identified (median wage, peer, YoY %, rate %)  
4. **Report ID + page number** (or Gateway fund+year identity for fund stories) logged  

### Stage E — Script & hook (0–60s)

- Max **~140 words** for short form  
- Structure:

| Time | Content |
|------|---------|
| 0:00–0:03 | Conversational hook with **exact $** and place (*Did you know [Place]…*) |
| 0:03–0:15 | Contrast (salary vs unaccounted funds; rate vs fixed income; etc.) |
| 0:15–0:45 | Narrative in **fair-report / SBOA terminology** only |
| 0:45–0:55 | **Proof path**: SBOA Report ID + page (or other primary ID) |
| 0:55–1:00 | CTA → audit.sboa.in.gov / gateway.ifionline.org / primary portal |

Visuals (when rendering): high-contrast $ overlay; document highlight; **permanent watermark** of report ID + page.

### Stages F & G — Human review & publish

- Generate **Human Review Card** (Obsidian + county queue): script, verified points, contrast, receipt paths.  
- **No publish** until human confirms: no unquoted criminal intent, zero fake vendors, proof path present.  
- APIs: `POST /county-queue/approve` · `reject` (reject auto-logs lesson — see continuous improvement).

### Stage H — Feedback loop

- Factual corrections → retract / correct immediately.  
- Audience comments = leads → verify in official DBs only.  
- `log_lesson` / reject reasons → `audit_pipeline_mistakes.yaml` → next run filter.  
- Full loop: `docs/CONTINUOUS-IMPROVEMENT.md`.

---

## MODULE 5 — NEVER DO THIS (hard constraints — abort publish)

1. **NEVER** treat aggregate fund names as private company payees.  
2. **NEVER** use criminal language (stole, embezzled, fraud, theft as allegation) unless **quoting** a formal charge.  
3. **NEVER** report on unfiled, unreleased, or draft audits.  
4. **NEVER** treat social media rumors as facts.  
5. **NEVER** lead with low-earning / seasonal public employees as the scandal.  
6. **NEVER** put IsolationForest / ECOD / method names in spoken hooks.  
7. **NEVER** publish without Human Review Card sign-off.  
8. **NEVER** claim the system “learned” unless a lesson is on disk (playbook files).

---

## MODULE 6 — ReClaw agent & file map

| Role | Path |
|------|------|
| Silent Auditor SOUL | `agents/silent_auditor/SOUL.md` |
| Detectors | `agents/silent_auditor/` · `tools/red_flag_engine.py` |
| Playbook (load every scan) | `tools/auditor_playbook.py` |
| Living truth | `data/content_truth_rules.yaml` |
| Mistakes / lessons | `data/audit_pipeline_mistakes.yaml` · `data/auditor_lessons_log.yaml` |
| This directive (machine) | `data/silent_auditor_workflow.yaml` |
| County skill | `.grok/skills/county-audit/SKILL.md` |
| Continuous improve | `docs/CONTINUOUS-IMPROVEMENT.md` |
| Blueprint | `data/indiana_public_finance_blueprint.yaml` |
| Source map | `data/public_source_map.yaml` |

### Ingestion → Ravenstack → RAG

1. Write/update vault note (`Ravenstack/ops/SILENT-AUDITOR-WORKFLOW.md`).  
2. Commit vault + repo.  
3. `rag_sync_vault` (MCP) or `POST /rag/vault/sync`.  
4. Agents retrieve via `query_knowledge` — **enforcement** still via playbook + code filters.

---

## MODULE 7 — Supersedes / cleanup

This document **supersedes** fragmented prompts and session notes for day-to-day agent behavior:

| Older material | Status |
|----------------|--------|
| `GEMINI-SILENT-AUDITOR-WORKFLOW-PROMPT*` | Archive / prompt only — point here |
| `SESSION-START-silent-auditor-*` | Historical session |
| Partial freeze notes without process | Keep freeze status in `content_truth_rules` + hot.md; process is here + continuous-improve |

Do **not** delete research archives; mark them historical and link here.

---

## Quick operator checklist

- [ ] SBOA cache has final special investigation for target county (if heat #1 path)  
- [ ] No draft/unfiled language in package  
- [ ] Actor named + $ exact + contrast + report ID/page  
- [ ] No Gateway rollup as vendor  
- [ ] No criminal verbs without charge quote  
- [ ] Human review card approved  
- [ ] On reject: specific reason (auto lesson)  

---

*SOT for Silent Auditor OpenClaw operations · update version + date when modules change*

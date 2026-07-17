---
name: county-audit
description: >
  Indiana county faceless-auditor workflow: Gateway truth, Firecrawl discovery,
  red-flag engine, Obsidian review cards, human approval. Use for county queue
  runs, audit tool discovery, SBOA ingest, detector implementation, Spencer/Vanderburgh
  packages, or "muni audit" / "red flag" / "watchdog video" tasks on ReClaw.
---

# County Audit — MuniAudit Workflow

Faceless YouTube factory for **92 Indiana counties**. Every flag traces to a public record. Human approves before publish.

## Master protocol (read first)

**SOT:** `docs/SILENT-AUDITOR-WORKFLOW.md` · vault `Ravenstack/ops/SILENT-AUDITOR-WORKFLOW.md` · machine `data/silent_auditor_workflow.yaml`

Covers: fair report + draft SBOA ban · source priority (SBOA I-series → 100R → township vendor → IURC → claims) · stages A–H · PHI · script 0–60s · hard never list · continuous improve.

## Non-negotiables

1. **County isolation** — Pike ingestion files never apply to other counties (`tools/county_isolation.py`).
2. **Provenance** — named entity or vendor + dollar + source row/PDF page. No category-only hooks.
3. **Obsidian SOT** — `/root/obsidian_vault/Rural Data/` review cards + packages.
4. **Human gate** — `POST /county-queue/approve` or `reject` before `run-next`.
5. **Continuous improve** — living playbook loaded every scan; every human reject becomes a durable lesson.

## Continuous improvement (mandatory)

Agents do **not** get better from chat history alone. They improve when lessons are written to disk and loaded on the next run (same pattern as AGENTS.md / learnings.md self-improving agent loops).

| Layer | Path | Who writes | Who reads |
|-------|------|------------|-----------|
| Truth | `data/content_truth_rules.yaml` | operator / research | `filter_flags_by_truth` |
| Mistakes | `data/audit_pipeline_mistakes.yaml` | `log_lesson` + humans | playbook open rules |
| Lessons log | `data/auditor_lessons_log.yaml` | auto on reject | operators |
| Code filter | `tools/auditor_playbook.py` | engineers | red_flag_engine + silent_auditor |

```bash
# Show what the next run will load
PYTHONPATH=. .venv/bin/python tools/auditor_playbook.py --show

# Manual lesson after research or operator feedback
PYTHONPATH=. .venv/bin/python tools/auditor_playbook.py \
  --log-id dry-hooks-gibson \
  --symptom "hooks were dry / no dual receipt" \
  --root-cause "flag factory volume not story juice" \
  --rule "SBOA + bill shock before salary mill"
```

**Reject path:** `POST /county-queue/reject` with reason **auto-calls** `log_lesson()` (county + reason → mistakes + lessons log). Do not skip the reason — it is the training signal.

**After a lesson:** fix detector/scriptwriter if needed, then `POST /county-queue/refresh` so the pending card uses new rules.

## Data tiers (what tool for what)

| Tier | Source | Tool | Never use for |
|------|--------|------|---------------|
| 1 | Gateway flat files | `indiana_gateway.py`, `dogegpt_budget.py` | — |
| 1 | Salaries | `gateway_salary_export.py` | cross-county fallback |
| 1 | USASpending/Census | `local_auditor_live.py` | primary headline |
| 2 | JS forms (Gateway salary) | httpx postbacks (already built) | — |
| 3 | SBOA PDFs, county sites | `firecrawl_discovery.py` / Firecrawl MCP | disbursement math |
| 4 | Human | review card + approve API | auto-publish |

## Firecrawl setup (this project)

- **API key** in `/root/ReClaw-2.0/.env` → `FIRECRAWL_API_KEY`
- **Grok MCP**: stdio `npx firecrawl-mcp` with key in `~/.grok/config.toml` (overrides plugin OAuth)
- **CLI**: `firecrawl search|scrape|map` (authenticated via env)
- **Python**: `from tools.firecrawl_discovery import discover_county_context, scrape_url`

**Use Firecrawl for:** SBOA audit PDF URL discovery, county `.in.gov` minutes/bids, DOR budget-order links.  
**Do NOT use for:** Gateway disbursements/budgets (flat file download is faster and canonical).

## Standard county workflow

```bash
cd /root/ReClaw-2.0

# 1. Prefetch if missing
PYTHONPATH=. .venv/bin/python scripts/export_county_salaries.py --county Spencer

# 2. Tier-3 discovery (optional, caches JSON)
export $(grep FIRECRAWL_API_KEY .env | xargs)
PYTHONPATH=. .venv/bin/python -c "
from tools.firecrawl_discovery import discover_county_context
print(discover_county_context('Spencer'))
"

# 3. Run audit package
curl -sf -X POST 'http://127.0.0.1:8000/run-sync?county=Spencer&write_obsidian=true'

# 4. Human reads review card in vault, then:
curl -X POST http://127.0.0.1:8000/county-queue/approve
# or reject with reason

# Refresh pending county after detector/scriptwriter updates:
curl -X POST http://127.0.0.1:8000/county-queue/refresh

# SBOA PDF discovery + download + finding extract (no Firecrawl required):
# Uses live API POST https://audit.sboa.in.gov:8090/filings/search
./scripts/run_sboa_discovery.sh Clark
PYTHONPATH=. .venv/bin/python tools/sboa_ingest.py Posey --download-top 3
# Cache: data/cache/sboa/{county}/manifest.json + *.pdf + *.txt
# Prefer SPECIAL INVESTIGATION (report numbers ending in I)

# Batch salary prefetch (89 counties still missing cache):
PYTHONPATH=. .venv/bin/python scripts/export_county_salaries.py --all
```

## Red-flag quality rules (from mistakes backlog + 2026-07-17 blueprint)

**SOT research:** vault `Ravenstack/ops/algorithmic-auditing-public-finance-blueprint-2026-07-17.md`  
**Machine:** `data/indiana_public_finance_blueprint.yaml` + `data/content_truth_rules.yaml`

**Publish-worthy hooks (priority):**
- SBOA final findings (special investigation / unsupported spend) with report ID + page
- Named salary outlier with **peer or median** contrast (Form 100R) — not Judge/Prosecutor state pay alone
- Dual-line compensation (same name, multi-dept) above blueprint thresholds
- Fund-specific YoY spike (named fund) with grant/bond offset kill
- Named vendor + date + amount **only** from claims dockets / township vendor report — never Gateway AFR ent_name

**Kill before scriptwriter (and before analysis when possible):**
- Category sum without vendor ("Other Capital Outlays $41M")
- Rollups: Governmental Activities, Transfers Out, WATER/GAS as payee
- Cross-county bleed (verify with `scripts/verify_county_isolation.py`)
- Benford-only with no named receipt
- Lifeguard/seasonal pay as scandal unless county-isolated and peer-outlier
- IsolationForest/ECOD method dumps as cold opens

## Implementation backlog

Read `data/audit_tool_candidates.yaml` before adding detectors. Priority order:

1. `sf-vendor-audit` procedures → Gateway disbursements
2. `pybenford` / `benfordslaw` → replace basic Benford
3. SBOA PDF ingest per county
4. `procurement-fraud-audit` rolling duplicates (when payment dates available)
5. OpenRefine-style vendor normalization

## Discovery workflow (find more tools)

```bash
cd /root/ReClaw-2.0
export FIRECRAWL_API_KEY=$(grep FIRECRAWL_API_KEY .env | cut -d= -f2)

# Web + GitHub leads
firecrawl search "site:github.com government vendor payment audit python" --limit 8 \
  -o .firecrawl/discover-vendor.json

# Indiana SBOA
firecrawl scrape https://audit.sboa.in.gov/ -o .firecrawl/sboa-index.md

# Log candidates in data/audit_tool_candidates.yaml (p0/p1/p2)
```

## Key paths

| Path | Purpose |
|------|---------|
| `data/cache/gateway_*` | Permanent Gateway flat files |
| `data/cache/salaries/salary_{code}_2025.csv` | Per-county salary cache |
| `data/cache/firecrawl/` | Tier-3 discovery JSON |
| `data/cache/sboa/{county}/manifest.json` | SBOA PDF links + finding excerpts |
| `tools/transaction_anomaly.py` | AP register rules + IF (inbox Layer 3g) |
| `tools/fiscal_health.py` | MSU-style budget ratios (Layer 3f) |
| `data/audit_tool_candidates.yaml` | Tool implementation backlog |
| `data/audit_pipeline_mistakes.yaml` | Lessons learned |
| `obsidian_vault/Rural Data/*-review-*-county.md` | Human review cards |

## MCP priority

1. `reclaw-platform__*` — vault, pipeline, health
2. `firecrawl` MCP or CLI — Tier-3 discovery
3. `reclaw-api__*` — county queue approve/reject
4. `github__*` — clone/evaluate candidate repos
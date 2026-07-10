# Practical operator roadmap (execution order)

**Last updated:** 2026-07-10

| # | Item | Status |
|---|------|--------|
| 1 | Fix RAG `query_knowledge` | **Done** (`rag/vectorstore.py` vault_only filter) |
| 2 | `morning_digest` + `county_queue_card` | **Done** (MCP extensions) |
| 3 | Phase B SuperGrok Automation pack | **Done** (docs + prompt + smoke); **UI schedule = human** |
| 4 | Permanent CF tunnel ± Access | **Scaffolded** — run named-tunnel script after `cloudflared login` |
| 5 | Gated queue approve/reject tools | **Done** (`confirm=true`) |
| 6 | Dashboard live status | **Done** (`status.json` + poller + timer) |
| 7 | Auto-issue from sitrep gaps | **Done** (`file_github_gaps` gated + `gh`) |

## Daily loop

1. SuperGrok Automation → `morning_digest`  
2. You review queue card if `awaiting_approval`  
3. Explicit OK for approve / GitHub file / pipeline  
4. Dashboard `:8081` shows live status.json  

## Human-only gates

Never from Automations: `county_queue_approve`, `county_queue_reject`, `county_queue_run_next`, `file_github_gaps`, `run_pike_winslow`.


## Verification (2026-07-10)

| Check | Result |
|-------|--------|
| `smoke_morning_digest.py` | OK · 41 tools |
| RAG vault_only search | hits |
| Dashboard `:8081` | LIVE status.json · CONNECTED · Gibson queue |
| Timer `reclaw-dashboard-status` | active (2 min) |
| Named CF tunnel | scaffold only — need `cloudflared tunnel login` |
| SuperGrok Automation UI | **you** create (prompt ready) |
| `file_github_gaps` | gated; dry_run OK |

_Updated: 2026-07-10T11:12Z_

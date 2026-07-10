# Design: SuperGrok Daily Operator Digest (Phase B)

**Date:** 2026-07-10  
**Status:** Draft for user review  
**Phase:** B (Operator path) — precedes Phase C (OpenClaw productization) and Phase D (visual dashboard)  
**Approach:** SuperGrok Task + ReClaw MCP connector (report-only day 1)

---

## 1. Purpose

Give the operator a **morning US** digest in SuperGrok that combines:

1. Full fortress status  
2. County queue focus  
3. OpenClaw / model health  
4. Gaps  
5. Top actions  
6. **Suggested** auto-actions (never executed without human OK)

Success = open SuperGrok (or notification if Automations supports push/email), read one structured report, decide what to do. No Build/SSH for routine status.

---

## 2. Architecture

```text
SuperGrok Automations (Tasks)
  schedule: morning America/Chicago (~7–9am; exact time set in UI)
       │
       ▼
  Task prompt (fixed contract)
       │
       ▼
  ReClaw Platform MCP connector (must be enabled for the task context)
       │
       ├── project_sitrep   (primary — plain English full status)
       └── pipeline_status  (optional if sitrep queue section thin)
       │
       ▼
  Digest rendered in SuperGrok task run output
  + push/email IF SuperGrok Automations product supports it
  + fallback: operator reads Automations run history (sufficient)
```

**Out of scope day 1:** Hetzner cron, Discord bot, auto-approve, auto pipeline run, required vault writes.

**In scope day 1:** Prompt contract, tool usage rules, digest schema, failure messaging, future hooks for vault log and gated actions.

---

## 3. Digest content (six blocks — mandatory)

Every successful run must produce:

### Block 1 — Overall
- Status emoji/label (healthy / healthy_with_gaps / degraded / down)  
- One-sentence executive summary  

### Block 2 — Stack (Docker / API / OpenClaw / MCP)
- From `project_sitrep`: containers, ReClaw API, OpenClaw gateway, MCP bridge/tunnel, Ollama if present, dashboard  

### Block 3 — County queue  
- Queue status, cursor, current county, pending review (county, risk, flag count, top finding 1 line)  
- Explicit line: **Human gate required** if `awaiting_approval`  

### Block 4 — OpenClaw / models  
- Default primary model (e.g. gemma4)  
- Note if sitrep/OpenClaw health signals issues  
- Not a full model catalog dump — health + “what’s active” only  

### Block 5 — Gaps  
- Bullet list from sitrep gaps + any connector failures  

### Block 6 — Actions  
- **Top 3 actions** for the operator today (ordered)  
- **SUGGESTED auto-actions** (0–N), each must include:  
  - What would run  
  - Why  
  - Risk  
  - Exact phrase operator should say to approve (e.g. “Approve Gibson queue” / “Run Pike/Winslow”)  
  - **Never execute** these in the automation run  

---

## 4. Tool and safety policy

### Allowed (day 1)

| Tool | Use |
|------|-----|
| `project_sitrep` | **Required** primary source |
| `pipeline_status` | Optional if queue detail missing |
| `sitrep` | Alias of project_sitrep |
| `connector_help` | Only if connector misconfigured |

### Forbidden (day 1 automation)

| Action | Rule |
|--------|------|
| `run_pike_winslow` | Never in daily task |
| County queue approve/reject | Never in daily task |
| `write_vault_file` / `ingest_*` | Never day 1 |
| `save_ravenstack_note` | **Not day 1**; **allowed later** as optional durable log after explicit product decision |
| Docker restart / shell | Never via SuperGrok task |
| Simulated sitrep | Never — if tools fail, say **DEGRADED** and why |

### Human approval principle (non-negotiable)

- Automation may **suggest** actions.  
- Operator **always** OKs before any mutation.  
- No “auto-approve if risk low” on day 1 or without a later dedicated design.

---

## 5. Task prompt contract (to paste into SuperGrok Automations)

Exact text for the operator (or install doc):

```text
You are the ReClaw fortress morning operator. Use the ReClaw / reclaw-platform MCP connector.

1. Call project_sitrep (no arguments). Do not invent health. Do not simulate.
2. If county queue detail is missing, call pipeline_status.
3. Produce a report with EXACTLY these headings:
   ## 1. Overall
   ## 2. Stack (Docker / API / OpenClaw / MCP)
   ## 3. County queue
   ## 4. OpenClaw / models
   ## 5. Gaps
   ## 6. Actions
4. In Actions: give Top 3 operator actions, then a subsection
   ### SUGGESTED auto-actions (require human OK)
   Each suggestion: what / why / risk / exact approval phrase.
   Do NOT run pipeline, approve queue, write vault, restart services, or any mutation.
5. If the connector fails: say DEGRADED, name the failure, tell the user to check
   ReClaw connector URL (data/mcp_public_url.txt on server) and that they must not use Build paste-workarounds as success.
6. Prefer the sitrep plain-English content; light rephrase OK. No raw multi-page JSON dumps.
```

**Schedule:** Morning America/Chicago; exact clock time set by operator in SuperGrok UI.

**Connectors:** ReClaw Platform MCP must be enabled for Automations/tasks (same public `/mcp` URL as chat; re-check if tunnel rotates).

---

## 6. Delivery

| Channel | Day 1 |
|---------|--------|
| SuperGrok Automations run output | **Required** |
| Push / email | **If product supports** — enable in UI; not a server dependency |
| Fallback | Operator opens SuperGrok Automations history — **acceptable** |
| Vault note | **Not required day 1**; **Phase B.2 optional** via `save_ravenstack_note` after operator enables it |

---

## 7. Failure modes

| Failure | Behavior |
|---------|----------|
| Connector offline / bad tunnel URL | DEGRADED message; no fake green status |
| `project_sitrep` errors | Report error text (trimmed); still list Top 3 as “fix connector / check gateway” |
| Partial tools | Fill available blocks; mark others `unknown (tool failed)` |
| Free model / OpenClaw issues | Surface under blocks 4–5; do not “fix” them in the task |

---

## 8. Future hooks (not day 1 implementation)

| Hook | Intent |
|------|--------|
| **B.2 Vault log** | Optional `save_ravenstack_note` or `Ravenstack/backlog/daily-sitrep-YYYY-MM-DD.md` after human enables |
| **B.3 Gated actions** | Separate design: operator replies “approve suggestion 1” in SuperGrok → explicit tool call; still no silent auto |
| **Phase C** | OpenClaw sub-agents / heartbeats UX productization |
| **Phase D** | Visual dashboard live state |

---

## 9. Components (isolation)

| Unit | Responsibility | Interface |
|------|----------------|-----------|
| SuperGrok Task | Schedule + prompt execution | Automations UI |
| MCP connector | Live read tools | `project_sitrep`, etc. |
| Digest schema | Six fixed headings | Prompt contract |
| Suggestion policy | Human OK only | Labeled suggestions, no mutate tools |
| Optional vault logger (later) | Durability | `save_ravenstack_note` |

---

## 10. Testing / acceptance

1. Manually run the task prompt once in SuperGrok (with connector on) — all six headings present.  
2. Confirm no mutation tools invoked.  
3. With connector disabled — output says DEGRADED, not fake healthy.  
4. Schedule morning run; operator can find result in Automations history.  
5. Suggestions (if any) include approval phrase and are not executed.

---

## 11. Implementation plan (high level — details in writing-plans later)

1. Write operator one-pager: exact prompt + schedule + connector checklist.  
2. Optional: tiny server helper that only **documents** current public MCP URL for the human (no auto task API unless xAI exposes one).  
3. Optional B.2: vault log skill/prompt variant.  
4. No OpenClaw/discord changes required for Phase B day 1.

**YAGNI:** No custom scheduler on Hetzner for SuperGrok Tasks. No auto-approve. No Hermes.

---

## 12. Decisions log

| Decision | Choice |
|----------|--------|
| Approach | SuperGrok Task + connector |
| Content | All six blocks |
| Delivery | SuperGrok + push/email if possible; chat history enough |
| Schedule | Morning US |
| Mutations | Report only; suggestions OK with human OK always |
| Vault log | Later optional (B.2) |

---

## Spec self-review

- [x] No TBD placeholders for day-1 behavior  
- [x] Consistent: suggestions allowed, mutations forbidden  
- [x] Scope limited to Phase B operator digest  
- [x] Ambiguity resolved: fallback delivery = SuperGrok history; vault not required day 1  

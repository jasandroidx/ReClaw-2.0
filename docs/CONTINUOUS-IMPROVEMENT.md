# Continuous improvement — how agents get better (operator process)

**Last updated:** 2026-07-17  
**Repo commit (wired):** `a12c39b`  
**Vault twin:** `Ravenstack/ops/CONTINUOUS-IMPROVEMENT-PROCESS.md`

---

## The short version

Agents **do not learn from chat**. They improve when:

1. You (or research) find a mistake  
2. That mistake is **written to a living rule file on disk**  
3. The **next county scan loads those files and enforces them in code**

If it isn’t on disk in the files below, the system did **not** “learn” it.

```
  RUN audit → write review card
       ↓
  HUMAN: approve  or  reject (with reason)
       ↓ reject
  auto log_lesson() → mistakes.yaml + lessons log
       ↓
  (optional) fix detectors / truth rules
       ↓
  NEXT RUN: load_playbook() → filter_flags_by_truth()
       ↓
  Fewer repeated fails; open mistakes stay visible
```

---

## Why this exists

We kept repeating the same fails (Gateway “WATER” as a vendor, IsolationForest cold opens, dry Gibson hooks) because lessons lived in **chat** or **notes agents never loaded into the flag path**.

Industry pattern (self-improving agents, AGENTS.md / learnings.md loops):

| Step | Meaning |
|------|---------|
| Act | Run the county / write shorts |
| Score | Human approve/reject or tests |
| Persist | Durable YAML / playbook, not chat |
| Inject | Load playbook at start of every scan |

---

## Living files (single source of truth for behavior)

All under `/root/ReClaw-2.0/data/`:

| File | What it is |
|------|------------|
| `content_truth_rules.yaml` | Hard kills, publish gate, heat rank, forbidden vendors/phrases |
| `audit_pipeline_mistakes.yaml` | Open + fixed lessons (symptom → root cause → rule) |
| `auditor_lessons_log.yaml` | Timestamped log (auto-filled on every reject) |
| `public_source_map.yaml` | Where receipts live (SBOA, DLGF, Gateway, etc.) |
| `indiana_public_finance_blueprint.yaml` | Hard_kill lists + story recipes |
| `audit_strategy.yaml` | High-level strategy |

**Code that enforces them every run:**

- `tools/auditor_playbook.py` — load, filter, log_lesson  
- `tools/red_flag_engine.py` — after detectors: `filter_flags_by_truth`  
- `agents/silent_auditor/agent.py` — same filter + session log  
- `core/county_queue.py` → `reject()` → auto `log_lesson()`

---

## Your day-to-day process

### A) Normal review (most important training signal)

1. Read the review card in Obsidian (`Rural Data/*-review-*`).  
2. **Approve** if hooks pass the bar (named actor + $ + contrast + receipt).  
3. **Reject with a specific reason** if not — e.g.  
   - `dry hooks, no dual receipt, salary mill only`  
   - `still treating Gateway rollups as vendors`  
   That reason is **automatically** written as a lesson.

```bash
# via API
curl -X POST http://127.0.0.1:8000/county-queue/reject \
  -H 'Content-Type: application/json' \
  -d '{"reason":"dry hooks — need SBOA named $ or rate shock, not method dumps"}'

# via MCP (confirm=true only when human asked)
# county_queue_reject(reason=..., confirm=true)
```

### B) After research or a new pattern

```bash
cd /root/ReClaw-2.0
PYTHONPATH=. .venv/bin/python tools/auditor_playbook.py --show

PYTHONPATH=. .venv/bin/python tools/auditor_playbook.py \
  --log-id short-slug-for-this-lesson \
  --symptom "what went wrong" \
  --root-cause "why" \
  --rule "what future runs must obey"
```

MCP: `log_auditor_lesson` (confirm=true), `auditor_playbook_show`.

If the filter alone isn’t enough, **change code** (detector kill list, scriptwriter publish gate), then refresh:

```bash
curl -X POST http://127.0.0.1:8000/county-queue/refresh
```

### C) After docs/rules change — keep knowledge searchable

1. Commit + push **ReClaw** repo  
2. Commit + push **Obsidian vault** (process notes under Ravenstack/)  
3. Re-index RAG:

```bash
# MCP: rag_sync_vault  (or reclaw-api rag_vault_sync)
```

RAG indexes **vault notes** for search. It does **not** replace the playbook filter. Quality rules still live in `data/*.yaml` + code.

---

## What improves vs what doesn’t

| Improves on next run | Does not auto-improve |
|----------------------|------------------------|
| Dropping known fake vendors / forbidden phrases | Inventing better story juice |
| Open mistakes listed in session context | Empty SBOA caches filling themselves |
| Reject reasons logged forever | Model weights / chat “memory” |

Juice still requires real sources: SBOA PDFs, rate ordinances, dual receipts. Continuous improvement = **stop repeating fails** + keep open mistakes visible until fixed.

---

## Tests

```bash
cd /root/ReClaw-2.0
PYTHONPATH=. .venv/bin/python -m pytest tests/test_auditor_playbook.py -q
```

---

## Related

- Skill: `.grok/skills/county-audit/SKILL.md` (Continuous improvement section)  
- Agent: `agents/silent_auditor/SOUL.md`  
- Routing: `AGENTS.md` → Continuous improvement  
- Blueprint: `data/indiana_public_finance_blueprint.yaml`  
- Vault: [[ops/CONTINUOUS-IMPROVEMENT-PROCESS]]

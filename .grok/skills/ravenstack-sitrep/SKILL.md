---
name: ravenstack-sitrep
description: >
  Full Ravenstack/ReClaw project sitrep via MCP connectors. Live stack health,
  git, knowledge, pipeline sessions, blockers, and next actions — distilled only.
  Use when the user says "use ravenstack-sitrep", /ravenstack-sitrep, sitrep,
  stack status, fortress status, or full project analysis.
---

# Ravenstack Sitrep

One-shot **situation report** for ReClaw 2.0 + Ravenstack Fortress. Always live from MCP — never invent health, never dump raw tool JSON.

## Non-negotiables

1. **MCP first** — prefer `ravenstack__*` (fallback: `reclaw-platform__*`). Shell only if MCP is down.
2. **Live every run** — re-query tools; do not reuse prior sitrep text as truth.
3. **Distill** — bullets, not logs. Cap each section; no full ORACLE paste.
4. **Mandatory sections** — use the template below, every time, in order. Empty → `none`.
5. **No mutations** unless the user explicitly asks (no ingest, no reload, no pipeline run).

## Procedure (run in parallel where possible)

Call `search_tool` first if schemas are unknown, then:

| Step | MCP tool | Purpose |
|------|----------|---------|
| 1 | `ravenstack__stack_health` | Full health snapshot |
| 2 | `ravenstack__git_status` | Branch / dirty state |
| 3 | `ravenstack__list_pipeline_sessions` (`limit`: 5) | Recent work |
| 4 | `ravenstack__list_knowledge_topics` | Knowledge surface |
| 5 | `ravenstack__query_knowledge` (`query`: `"current blockers OR open backlog OR known issues"`, `top_k`: 4) | Context for risks |
| 6 | Optional if step 1 incomplete | `docker_status`, `reclaw_health`, `openclaw_health` |

Fallback prefix: `reclaw-platform__` with the same tool names.

If MCP is unavailable: one shell pass only —

```bash
cd /root/ReClaw-2.0 && ./scripts/post-deploy-healthcheck.sh 2>/dev/null; git status -sb; ls -1 data/sessions 2>/dev/null | tail -5
```

Mark the sitrep **DEGRADED (shell fallback)**.

## Output template (mandatory — fill every section)

```markdown
# Ravenstack Sitrep
**As of:** <ISO timestamp UTC> · **Overall:** 🟢 healthy | 🟡 degraded | 🔴 down

## 1. Stack health
- ReClaw API:
- OpenClaw gateway:
- Ollama / LLM:
- Docker compose:
- Other (Tailscale, dashboard):

## 2. Repo
- Branch:
- Dirty?:
- Note: (1 line max)

## 3. Knowledge / vault
- Topics count or key anchors:
- ORACLE reachable?: yes/no
- RAG signal: (1 line from query, or none)

## 4. Recent pipeline
- Last N sessions (id · age · county if known):
- Stuck / failed:

## 5. Blockers & red flags
- (severity · fact · source). Or: none

## 6. Next actions
1. …
2. …
3. …  (max 3, actionable, ordered)

## 7. Provenance
- Tools used: (list)
- Fallback used?: no | shell
```

### Distill rules

- Status emoji from worst live signal only.
- Health: `up` / `down` / `unknown` + one number or phrase (latency, exit, version) — no multi-line dumps.
- Sessions: max 5 lines.
- Blockers: only confirmed from tools or cited knowledge hits.
- Next actions: revenue/ops first; skip fluff.
- Total sitrep target: **≤ 40 lines**.

## Optional follow-ups (only if user asks)

| Ask | Tool |
|-----|------|
| Deep ORACLE | `ravenstack__read_oracle` (section optional) |
| Save sitrep to vault | distill → `ravenstack__save_ravenstack_note` (`source`: `sitrep`, `potential_for`: `ops`) |
| Reload after fixes | `ravenstack__reload_ritual` |
| Run pipeline | do **not** auto-run; hand off to reclaw-build / explicit command |

## Paths (reference only)

| Path | Role |
|------|------|
| `/root/ReClaw-2.0` | Repo |
| `/root/obsidian_vault/Ravenstack/` | Knowledge SOT |
| `data/sessions/` | Pipeline isolation |
| `data/reclaw_orchestration.yaml` | Deployed vs backlog map |

## Anti-patterns

- Pasting full `stack_health` JSON into chat
- Treating skill file text as live status
- Running rural_data / ingest during a sitrep
- Skipping sections or inventing green health

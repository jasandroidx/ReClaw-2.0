---
name: ravenstack-sitrep
description: >
  Use when the user wants live Fortress status: sitrep, fortress sitrep,
  fortress status, stack status, full project status, full analyze, morning
  check, "is everything ok", /ravenstack-sitrep, or ravenstack-sitrep. Covers
  Docker, Tailscale, OpenClaw, ReClaw API, MCP, Ollama, queue, git, vault, gaps.
---

# Fortress Sitrep — full live status

**Core principle:** Always probe live. Never invent health. **Fortress** = entire stack (OpenClaw + ReClaw + repo + Ravenstack + Docker + Tailscale + MCP + nodes) — not OpenClaw alone.

**REQUIRED:** Call tools **this turn**. Prior sitrep text is not truth.

## When to use / when not

| Use | Not this skill |
|-----|----------------|
| Status, sitrep, “what’s broken?”, morning check | **Fix/wire/deploy** → skill `openclaw-mechanic` |
| Full fortress audit before a big decision | **County flags/scripts** → `county-audit` |
| User says fortress status / stack status | Mutations (approve queue, restart) unless they ask after |

## Non-negotiables

1. **Always live** — call tools now.
2. **MCP first** — `reclaw-platform__*` (fallback `ravenstack__*`). Shell only if MCP down.
3. **One-shot full pass** — `project_sitrep` first (or `morning_digest` for SuperGrok brief). Fill holes only if thin/failed.
4. **Show the report** — tool markdown is the answer; light rephrase only.
5. **No mutations** — no pipeline run, approve, ingest, or write unless user asks after.
6. **Gaps mandatory** — every degraded layer in blockers with severity.
7. **Secrets** — never print gateway tokens or API keys.

## Procedure

### A — Primary (always)

```
reclaw-platform__project_sitrep
```

(or `ravenstack__project_sitrep` / `sitrep`)

### B — Fill holes (only if A failed / empty)

| Layer | Tool |
|-------|------|
| Stack | `stack_health` |
| Docker | `docker_status` |
| OpenClaw | `openclaw_health` |
| MCP | `connector_status` |
| Pipeline | `pipeline_status` |
| Session | `inspect_session` (empty id = latest) |
| Git | `git_status` / `git_vault_status` |
| Models | `openclaw_models` |

### C — Shell fallback (MCP down only)

```bash
cd /root/ReClaw-2.0
./scripts/post-deploy-healthcheck.sh
docker compose ps
tailscale status | head
systemctl is-active reclaw-mcp-bridge reclaw-mcp-tunnel
curl -sf http://127.0.0.1:8000/health
curl -sf http://127.0.0.1:18789/health || true
```

Mark report **DEGRADED (shell fallback)**.

## Output

1. Call `project_sitrep`.
2. Present tool result (plain English sections).
3. If tool failed: B/C then same coverage yourself.
4. End with **top blockers + one next action** if not already clear.

## Triggers

| User says | You do |
|-----------|--------|
| sitrep / fortress sitrep / fortress status | Full `project_sitrep` |
| /ravenstack-sitrep | same |
| stack status / full analyze / is everything ok | same |
| just API/docker health | `stack_health` or `docker_status` only if they scoped it |

## After sitrep (only if asked)

| Ask | Action |
|-----|--------|
| Save to vault | `save_ravenstack_note` source=`sitrep` |
| Fix what’s broken | Hand off to **`openclaw-mechanic`** (or run mechanic procedure) |
| Put report in outbox | Write under `/root/outbox` → `http://100.108.130.82:8765/` |
| Approve queue / run pipeline | Explicit human intent only |

## Anti-patterns / red flags

- Partial “API is fine” without Docker/Tailscale/MCP/queue/git/vault
- Treating skill text or chat memory as live status
- Dumping raw multi-page JSON
- Auto-running pipeline or writes
- Skipping gaps when queue is `awaiting_approval` or tunnel inactive
- Claiming models/primary without probe

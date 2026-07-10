---
name: ravenstack-sitrep
description: >
  FULL live ReClaw/Ravenstack project status analysis via MCP connector: Docker,
  Tailscale, OpenClaw gateway, ReClaw API, MCP bridge/tunnel, Ollama, fortress
  dashboard, county queue, sessions, packages, git (repo+vault), GitHub, Obsidian
  knowledge, RAG, gaps, and next actions. Use when the user says
  "use ravenstack-sitrep", /ravenstack-sitrep, sitrep, full project status,
  fortress status, stack status, full analyze, or "status update on ReClaw".
---

# Ravenstack Sitrep — Full Project Live Status

When this skill is invoked you run a **complete live audit of the entire ReClaw / Ravenstack fortress**. Not a partial health ping. Cover every layer below. Prefer MCP. Never invent status.

## Non-negotiables

1. **Always live** — call tools now; never reuse prior sitrep text as truth.
2. **MCP first** — `reclaw-platform__*` preferred (fallback `ravenstack__*`). Shell only if MCP down.
3. **One-shot full pass** — call `project_sitrep` first (covers everything). For SuperGrok morning brief, prefer `morning_digest`. Supplement if any section is thin.
4. **Distill for chat** — structured report from live data; no multi-KB raw dumps. Facts only.
5. **No mutations** — no ingest, reload, pipeline run, approve, or write unless user explicitly asks after the sitrep.
6. **Gaps are mandatory** — every missing/degraded layer goes in Blockers & gaps with severity.

## Procedure (mandatory)

### Step A — Primary (always)

```
reclaw-platform__project_sitrep
```
(or `ravenstack__project_sitrep` / `sitrep`)

**The tool returns a full plain-English markdown report** (all 16 sections already written).  
In chat: **show that report to the user**. Do not invent status; light rephrase only if needed.

### Step B — Fill holes (parallel if needed)

Only if Step A failed or a section is empty/error:

| Layer | Tool / action |
|-------|----------------|
| Stack shell snapshot | `stack_health` |
| Docker only | `docker_status` |
| OpenClaw | `openclaw_health` |
| Pipeline | `pipeline_status` |
| Session deep | `inspect_session` (empty = latest) |
| Repo dirty | `git_status` |
| Knowledge list | `list_knowledge_topics` |
| ORACLE | `read_oracle` section `MCP Connector` |
| RAG | `query_knowledge` query `MCP connector blockers` |
| Vault file | `read_vault_file` `Rural Data/_latest.md` |

### Step C — Shell fallback (only if MCP unavailable)

```bash
cd /root/ReClaw-2.0
./scripts/post-deploy-healthcheck.sh
docker compose ps
tailscale serve status; tailscale ip -4
systemctl is-active reclaw-mcp-bridge reclaw-mcp-tunnel
git -C /root/ReClaw-2.0 status -sb
git -C /root/obsidian_vault status -sb
gh repo view jasandroidx/ReClaw-2.0 --json name,updatedAt,url 2>/dev/null
curl -sf http://127.0.0.1:8000/health; curl -sf http://127.0.0.1:18789/health
curl -sf http://127.0.0.1:8000/county-queue/status | head -c 800
```

Mark sitrep **DEGRADED (shell fallback)**.

## Output (mandatory)

1. Call `project_sitrep` (or `sitrep`).
2. **Present the tool result as the answer** — it is already plain English with sections 1–16.
3. Only if the tool failed: use Step B/C and then fill the same section list yourself.

### Distill rules

- Prefer the tool’s markdown as-is.
- Secrets: never print gateway tokens or API keys.
- No mutations after sitrep unless the user asks.

## Chat triggers (seamless)

| User says | You do |
|-----------|--------|
| use ravenstack-sitrep | Full template from `project_sitrep` |
| /ravenstack-sitrep | same |
| full project status / fortress status / sitrep | same |
| use ravenstack connector to project_sitrep | Call tool; still render full template |
| use ravenstack connector to stack_health | Health only unless they asked for full sitrep |

## After sitrep (only if asked)

| Ask | Tool |
|-----|------|
| Save to vault | `save_ravenstack_note` source=`sitrep` |
| Reload | `reload_ritual` / `python -m core.cell` |
| Run pipeline | explicit user command only |
| Approve county queue | explicit human gate only |

## Anti-patterns

- Partial “API is fine” without Docker/Tailscale/MCP/queue/git/vault
- Treating skill text as live status
- Dumping raw multi-page JSON into chat (summarize `project_sitrep`)
- Auto-running pipeline or writes
- Skipping gaps when queue is `awaiting_approval`

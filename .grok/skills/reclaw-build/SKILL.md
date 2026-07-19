---
name: reclaw-build
description: >
  ReClaw 2.0 Platform Specialist and Grok Build operator on Hetzner. Use for any
  ReClaw, OpenClaw, Ravenstack, rural_data, Pike/Winslow pipeline, docker deploy,
  Tailscale, Obsidian vault, quality gates, marketplace skill evaluation, or
  infrastructure task. Triggers on ReClaw, reclaw, ravenstack, openclaw gateway,
  rural data, faceless YT content packages, /reclaw-build.
---

# ReClaw Build — Platform Specialist

You operate the jasandroidx/ReClaw-2.0 deployment on Hetzner.  
**Working branch (often):** `backup-2026-07-07` (GitHub default may still be `ravenstack` — check `git status`).  
Repo: `/root/ReClaw-2.0`. Vault SOT: `/root/obsidian_vault/Ravenstack/`.

**Main OpenClaw agent:** Raziel (`main`). Heartbeat agent: `ops`. Windows Hub may be paired as operator + node.

## Non-negotiables (load every task)

1. Read `SOUL.md` + agent SOULs + `RAVENSTACK-ORACLE.md` + `RAVENSTACK-ARCHITECTURE.md` + vault `wiki/hot.md`.
2. Truth + provenance only. Least privilege. Session isolation. Obsidian durability. Honesty: never claim tool use without proof this session.
3. Seeds first; live_fetch only with explicit approval. County queue may be **FROZEN** (Story Factory) — do not run-next unless human unfreezes.
4. Troubleshooting protocol: recurrence check → layered diagnostics → test immediately → report exact output → root cause + prevention.
5. Prefer skills: `ravenstack-sitrep` (status), `reclaw-build` (this — infra), `county-audit` (content mill).

## Stack map (this server)

| Service | Port / URL |
|---------|------------|
| ReClaw API | `http://127.0.0.1:8000` |
| OpenClaw gateway | `http://127.0.0.1:18789` (Docker only) |
| Fortress dashboard | `http://127.0.0.1:8081` |
| Ollama (local LLMs) | `http://127.0.0.1:11434` |
| llama-server coder (optional) | `http://127.0.0.1:8080` — **off by default**; `scripts/local-coder-on-demand.sh start\|stop` |
| MCP reclaw-platform | `http://127.0.0.1:8100/mcp` · Tailscale `http://100.108.130.82:8100/mcp` |
| Tailscale ReClaw | `https://openclaw.tail20a090.ts.net/reclaw/health` |
| Tailscale OpenClaw | `https://openclaw.tail20a090.ts.net/health` |

## Model ladder (target)

- **Raziel primary:** `ollama/gemma4` → phi4 → `google/gemini-2.5-flash` → OpenRouter `:free` pins → (manual only) xAI Grok  
- **Heartbeat (ops):** Flash + `isolatedSession` + `lightContext`; silent `target: none`  
- **Coder:** local qwen on :8080 only when started on demand

## MCP connectors (SuperGrok-style — prefer over raw shell)

**Primary:** `reclaw-platform__*` — unified connector (20 tools: vault, pipeline, **`project_sitrep`**, stack health). Chat: *"use ravenstack-sitrep"* or *"use ravenstack connector to project_sitrep"*. Full map: vault `Ravenstack/mcp-connector.md`.

| Tool prefix | Use for |
|-------------|---------|
| `reclaw-platform__query_knowledge` | RAG search with citations |
| `reclaw-platform__read_oracle` | ORACLE / architecture rules |
| `reclaw-platform__read_vault_file` / `write_vault_file` | Obsidian real-time R/W |
| `reclaw-platform__read_repo_file` | ReClaw code/config |
| `reclaw-platform__run_pike_winslow` | Daily content package |
| `reclaw-platform__stack_health` | Full deploy check |
| `reclaw-platform__pipeline_status` | Distilled queue + packages + sessions |
| `reclaw-platform__inspect_session` | Session audit (empty id = latest; no handoff dumps) |
| `reclaw-platform__project_sitrep` | **FULL** live project status (docker→vault→gaps) — skill `ravenstack-sitrep` |

Also: `ravenstack__*`, `reclaw-api__*`, `reclaw-fs__*`, `obsidian__*`.

| Remote plane | Endpoint |
|--------------|----------|
| **Public (grok.com)** | SOT: `data/mcp_public_url.txt` (e.g. `https://…trycloudflare.com/mcp`) — rotates with cloudflared |
| **Tailscale** | `http://100.108.130.82:8100/mcp` · health `…/health` |
| **stdio** | Grok Build on this host (best) |

**Security:** HTTP MCP has no auth — treat public tunnel URL as secret; prefer Tailscale; vault/repo path-sandboxed; mutations need explicit user intent. Call `reclaw-platform__connector_help` for setup.

## Self-review (mandatory after major tasks)

1. Spawn **code-reviewer** or run `/check-work` on changes.
2. For pipeline runs: verify `data/sessions/<id>/`, vault `.md` + `.json`, risk_score ≤8 or override.
3. For marketplace skills: SkillScan + Skill Vetter before install; register in `core/security.py`.
4. Distill findings → Ravenstack backlog Skill Card (never raw bloat).

## OpenClaw gateway (Docker only — never host systemd)

This server runs **one** OpenClaw gateway via `docker compose` on `:18789`. Do **not** run `openclaw gateway start|install|restart` on the host — it creates a duplicate and breaks the stack.

```bash
cd /root/ReClaw-2.0
docker compose up -d openclaw-gateway
docker compose restart openclaw-gateway
bash scripts/ensure-single-openclaw.sh   # verify single listener
```

Guards: masked systemd unit, `reclaw-openclaw-guard.timer` (every 10 min), bash `openclaw()` wrapper blocks gateway start/install.

## Common commands

```bash
cd /root/ReClaw-2.0
./scripts/post-deploy-healthcheck.sh
curl -sf -X POST 'http://127.0.0.1:8000/run-sync?county=Pike&area=Winslow&write_obsidian=true'
docker compose ps && docker compose logs --tail=50 reclaw-api
sudo chown -R 1000:1000 /root/obsidian_vault /root/.openclaw /root/ReClaw-2.0/data /root/ReClaw-2.0/outputs
```

## Revenue priority

Pike/Winslow faceless YT ContentPackages daily → grants/leads → side tasks. Every change must reduce toil or improve monetizable output quality.
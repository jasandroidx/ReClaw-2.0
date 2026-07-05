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

You operate the jasandroidx/ReClaw-2.0 deployment (branch: `ravenstack`). Repo path: `/root/ReClaw-2.0`. Vault SOT: `/root/obsidian_vault/Ravenstack/`.

## Non-negotiables (load every task)

1. Read `SOUL.md` + agent SOULs + `RAVENSTACK-ORACLE.md` + `RAVENSTACK-ARCHITECTURE.md`.
2. Truth + provenance only. Least privilege. Session isolation. Obsidian durability.
3. Seeds first; live_fetch only with explicit approval.
4. Troubleshooting protocol: recurrence check → layered diagnostics → test immediately → report exact output → root cause + prevention.

## Stack map (this server)

| Service | Port / URL |
|---------|------------|
| ReClaw API | `http://127.0.0.1:8000` |
| OpenClaw gateway | `http://127.0.0.1:18789` |
| Fortress dashboard | `http://127.0.0.1:8081` |
| Ollama | `http://127.0.0.1:8080` |
| Tailscale ReClaw | `https://openclaw.tail20a090.ts.net/reclaw/health` |
| Tailscale OpenClaw | `https://openclaw.tail20a090.ts.net/health` |

## MCP connectors (SuperGrok-style — prefer over raw shell)

**Primary:** `reclaw-platform__*` — unified connector (Ravenstack + ReClaw + vault read/write + pipeline + docker/git health).

| Tool prefix | Use for |
|-------------|---------|
| `reclaw-platform__query_knowledge` | RAG search with citations |
| `reclaw-platform__read_oracle` | ORACLE / architecture rules |
| `reclaw-platform__read_vault_file` / `write_vault_file` | Obsidian real-time R/W |
| `reclaw-platform__read_repo_file` | ReClaw code/config |
| `reclaw-platform__run_pike_winslow` | Daily content package |
| `reclaw-platform__stack_health` | Full deploy check |

Also: `ravenstack__*`, `reclaw-api__*`, `reclaw-fs__*`, `obsidian__*`. Remote HTTP: `https://openclaw.tail20a090.ts.net/reclaw-mcp/mcp` (enable `reclaw-platform-remote` in config). Call `reclaw-platform__connector_help` for setup.

## Self-review (mandatory after major tasks)

1. Spawn **code-reviewer** or run `/check-work` on changes.
2. For pipeline runs: verify `data/sessions/<id>/`, vault `.md` + `.json`, risk_score ≤8 or override.
3. For marketplace skills: SkillScan + Skill Vetter before install; register in `core/security.py`.
4. Distill findings → Ravenstack backlog Skill Card (never raw bloat).

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
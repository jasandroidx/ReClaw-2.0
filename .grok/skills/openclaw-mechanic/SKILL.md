---
name: openclaw-mechanic
description: "Fix, deploy, wire, upgrade Fortress (OpenClaw/ReClaw/Docker/MCP)."
---

# OpenClaw Mechanic — Fortress operator

**Core principle:** Probe live truth, mutate least, never invent status, never second-gateway. The **Fortress** is the whole stack (OpenClaw + ReClaw + repo + Ravenstack + Docker + Tailscale + MCP + nodes).

**Violating the letter of these rules is violating the spirit.**

## When to use / when not

| Use | Not this skill |
|-----|----------------|
| Broken gateway, MCP, Tailscale, models, devices | **Status only** → skill `ravenstack-sitrep` |
| Deploy/restart, openclaw.json, auth, wiring | **County flags/scripts/queue content** → `county-audit` |
| “Best way to run/add X on this stack” | Pure product Story Factory design without ops |
| User says mechanic / reclaw-build / fix the stack | |

If status is unclear before a fix: **REQUIRED SUB-SKILL:** `ravenstack-sitrep` (or `project_sitrep`) first.

## Non-negotiables

1. **Honesty** — never claim checked/fixed/healthy without tool proof this turn. Lead with failures.
2. **Single gateway** — only Docker `openclaw-gateway`. Never host `openclaw gateway install|run`.
3. **Probe before mutate** — docker/health/models/devices as relevant; backup config before edits.
4. **Ownership** — after root writes under `~/.openclaw`, `chown 1000:1000` (linuxbrew) so container can read.
5. **Secrets** — never print full API keys/tokens. Prefer auth profiles over pasting keys.
6. **County freeze** — do not run-next/unfreeze queue unless Jason explicitly unfreezes Story Factory.
7. **Delivery** — “send it to me” / outbox → `/root/outbox` + `http://100.108.130.82:8765/`. Email only if asked.

## Procedure (every ops task)

1. **Classify** — fix / wire / upgrade / advise / deploy.
2. **Sitrep if unclear** — `reclaw-platform__project_sitrep` or skill `ravenstack-sitrep`.
2b. **Known breakage** — grep `Ravenstack/ops/incidents/INDEX.md` (or `query_knowledge`) for the symptom **before** mutating. After a real fix, add/update a card.
3. **Backup** — timestamped copy of `openclaw.json` (or other target) before change.
4. **Mutate least** — prefer `docker exec openclaw-gateway openclaw …` (matches 2026.7.x) over host CLI.
5. **Verify** — health, `ensure-single-openclaw.sh`, `models status`, device list, exact command output.
6. **Report** — status · evidence · residual risk · one next step. Distill durable notes to Ravenstack when meaningful.

## Quick runbooks

Full commands: `references/runbooks.md`.

| Job | First move |
|-----|------------|
| Gateway | `cd /root/ReClaw-2.0 && docker compose ps` · `bash scripts/ensure-single-openclaw.sh` · restart only compose service |
| Devices/nodes | `docker exec openclaw-gateway openclaw devices list` · `approve <id>` · same for `nodes approve` |
| Models/auth | `models status` (live) · `models auth paste-api-key` via stdin/env · never echo keys · do not trust skill-text model ladders |
| MCP tunnel | `systemctl status reclaw-mcp-bridge reclaw-mcp-tunnel` · public URL SOT `data/mcp_public_url.txt` |
| Config edit | backup → edit → `chown 1000:1000` → `config validate` → restart if needed |

## Paths (anchors)

- Repo: `/root/ReClaw-2.0` (branch often `backup-2026-07-07` — check git)
- Vault: `/root/obsidian_vault/Ravenstack/` · first-read `wiki/hot.md`
- OpenClaw state: `/root/.openclaw/` · workspace Raziel SOUL
- Outbox: `/root/outbox` → `http://100.108.130.82:8765/`

Stack map / MCP planes: vault `mcp-connector.md` + `references/runbooks.md` (not frozen model lists).

## Peer skills

- **Status:** `ravenstack-sitrep`
- **Content mill:** `county-audit`
- **This skill:** fix / build / optimize / advise

## Red flags — STOP

- About to invent health or primary model from memory
- About to run `openclaw gateway` on the host
- About to edit `openclaw.json` as root without chown
- About to print a full secret
- About to advance frozen county queue
- About to skip sitrep when the user asked “is it broken?”
- About to email when they said “send it” / outbox
- About to bind anything to `:8100` or `fuser -k` / kill the process on 8100
- About to enable `raven-mcp-bridge` or run `tools/raven_bridge_server.py`

## Rationalizations

| Excuse | Reality |
|--------|---------|
| “I know primary is still gemma4” | Run `models status` / MCP `openclaw_models` every time. |
| “Host openclaw with --token is fine” | Host binary may be older; use container CLI. |
| “Hurry — skip backup” | Backup is seconds; recovery is not. |
| “Env key is enough forever” | Prefer auth profile; dual is transitional. |
| “Sitrep skill not needed” | Status skill exists; use it for full picture. |

## Self-review (after major work)

Verify with live probes; optional `/check-work` on code diffs; distill to vault. Never claim done without evidence.

# ReClaw 2.0

**General-purpose agent operating platform** (OpenClaw-pattern aligned) with initial rural-data workflow module. A clean, production-grade foundation.

**Repo**: https://github.com/jasandroidx/ReClaw-2.0

ReClaw 2.0 provides domain-agnostic core (Gateway, Session isolation, Security/approval gates, Obsidian durable memory, event model for future visual frontend). The current repo implements rural_data (county research, red-flag analysis, content packages) as the first concrete module. Future domains (grants, local_leads, content, research_packets, visual office) add cleanly under agents/<domain>/ without changing core.

Later phases add Scriptwriter, Visuals, business automation services, and the visual agent office layer. Phase 1 = clean foundation only.

## Core Principles (from SOUL.md)
- Truth + provenance only. No hype.
- Least privilege + explicit approval gates for anything risky.
- Session isolation for every run (full audit trail on disk).
- Obsidian is the durable output + human review surface.
- Docker + Tailscale on Hetzner GPU box = prod. Local PC = identical dev mirror.
- Small, readable, extendable Python. No bloat.

## Current Implementation (MVP rural_data module)
Core platform is domain-agnostic. This module demonstrates the patterns:
- **Researcher** (`agents/researcher/`) — pulls or loads seed data → ResearchPackage (JSON)
- **Analyst / Red Flag** (`agents/analyst/`) — turns research into insights + red flags + channel angles → AnalysisPackage
- **Light Orchestrator** — sequences them, enforces quality gates from SOUL, assembles ContentPackage, writes to Obsidian channel
- **Gateway** (`api/main.py`) — the control plane. Creates sessions, loads identities, manages permissions/approvals, exposes HTTP for triggers + status + future event feed.

See AGENTS.md for routing and core/platform capabilities. Future domains live in parallel under `agents/`.

## Quick Start (Local)

```bash
cp .env.example .env
# edit OBSIDIAN_VAULT_PATH to point at your vault (or leave as outputs/obsidian for testing)

pip install -r requirements.txt

# Full end-to-end with seeds (safest)
python -m reclaw.cli run --county Pike --area Winslow

# Via the Gateway (also creates full session + approval records)
python -c "
from api.main import run_sync
print(run_sync('Pike', 'Winslow'))
"
```

The markdown package will be written directly into your configured Obsidian folder under the "Rural Data" subdir (or whatever you set in .env).

## Production on Hetzner

See [docs/SETUP.md](docs/SETUP.md) and [docs/tailscale.md](docs/tailscale.md).

```bash
docker compose up -d
# Then hit the Gateway over Tailscale
curl -X POST "https://your-reclaw-box.ts.net/trigger/Pike?auto_approve=true"
```

## Key Folders

- `agents/<name>/SOUL.md` — identity loaded by every run of that agent (OpenClaw style)
- `core/handoff.py` — the strict JSON contract between agents (ResearchPackage, AnalysisPackage, ContentPackage)
- `core/security.py` — capability registry + approval gate implementation
- `core/session.py` — isolation: every run gets `data/sessions/<id>/` with souls, handoffs, approvals, logs
- `data/seeds/` — deterministic test data for Pike/Winslow (and future counties)
- `data/runs/` + `data/sessions/` — the full audit history
- `docs/SECURITY.md` — how the gates and Docker sandboxing work
- `docker-compose.yml` + `docker/Dockerfile` — GPU-ready, non-root, volume layout for Hetzner

## Handoff Example

All agents talk only via the Pydantic models serialized to JSON files inside the session `handoffs/` dir (or returned directly).

See `examples/sample_research_output.json` and the generated packages in your vault.

## Security Highlights

- Live fetches are medium risk and go through the gate (see `SecurityManager.request_approval`).
- No agent can write outside its session or the approved obsidian path.
- Every grant and every capability use is logged.
- `POST /sessions/<id>/approve` is the human/bot approval endpoint on the Gateway.

Full details: [docs/SECURITY.md](docs/SECURITY.md)

## Extending

1. Add a new agent dir with its own `SOUL.md`
2. Declare its capabilities in `core/security.py`
3. Update `AGENTS.md` routing
4. Wire it in the Orchestrator or a future richer pipeline
5. Add to docker-compose if it needs extra resources

When we add the business services side (GBP for auto shops etc.), they will live in a parallel tree but use the exact same Gateway, session, security, and handoff patterns.

## Ravenstack Fortress Dashboard (Final Production UI - ravenstack branch)

**Mystical stone/neon pixel RPG hall** at http://100.119.160.116:8080 (or localhost:8080). Central Ravenlord orchestrator, 3 distinct chambers:
- **Clawforge** (blacksmith 🔨 with hammerStrike animation + sparks via CSS/JS particles)
- **Grant Hall** (scribe 📜 with quillGlow + glowing effects)
- **Knowledge Vault** (archivist 🏮 with lanternPulse + pulsing shelves/holographics)

Hover/click for feedback, live #log with WS to gateway:18789 (cell events from core/cell.py:399), Ravenlord side panel with buttons for Generate Video Script (rural Indiana faceless), MD Summary/Obsidian Export, Scan Flows/Audit, Call Assembly, Refresh Agents. All self-contained in single index.html with **CONFIG** object at top for easy expansion (add rooms without rewrite — data-driven).

**Cache-proof**: meta no-cache headers, version in title/CONFIG (2026.06.19-final), hard refresh (Ctrl+Shift+R).

**Canonical source of truth**: `/root/ReClaw-2.0/dashboard/index.html` (synced to `/opt/reclaw/dashboard` for Docker volume). Old versions (/opt/reclaw/dashboard/dist, index.html.old, ReClaw-Vault, safe backups, Station House React build) archived/killed.

**One-command rebuild** (new self-improvement for Grok Build):
```bash
# Diagnosis + clean + build + deploy + verify + git
cd /root/ReClaw-2.0 && ./tools/rebuild-fortress-dashboard.sh
```
(or use the new `fortress-dashboard` skill via Grok: `/fortress-dashboard rebuild`).

**Grok Build Self-Improvement Implemented**:
- Reusable `~/.grok/skills/fortress-dashboard` skill with auto-detect serving folder (lsof -i:8080 + docker inspect), cache-busting, full HTML regen from template.
- Support for Phasor.js (lightweight via CDN in future iterations; current CSS+Canvas fallback for pixel RPG: hammer swing, particle emitters for sparks/torches).
- Integration hooks: WS to OpenClaw gateway:18789, calls to ReClaw skills (clawsmith, silent_auditor via events).
- Auto-kill stale servers (python http.server, node proxies, docker), archive old index/dist.
- Documented in README + obsidian_vault/RAVENSTACK-ARCHITECTURE.md. Turns manual overwrites into robust repeatable system. Search ClawHub yielded no exact match so built custom wrapper (control-ui-e2e patterns reused for verification).

Test: `curl -I http://localhost:8080` (expect Ravenstack title), hard refresh in browser/incognito. `docker compose logs reclaw-dashboard`. Git on ravenstack updated.

See `/root/ReClaw-2.0/dashboard/index.html:234` for CONFIG, `core/cell.py:399` for event bus. Future: full Phaser 3 canvas RPG with tweens/particles via skill extension.

This fixes all prior cache/stale copy/Docker/proxy issues permanently.

## Status

MVP complete:
- Folder structure + identities
- Two core agents + light orchestrator with quality gates
- Clean JSON handoffs
- Obsidian writer
- Gateway with approval endpoints
- Docker + GPU compose
- Tailscale + security docs
- Pike/Winslow seed data + runnable examples

Next: real live county fetchers (one source at a time), Scriptwriter agent, first faceless channel episodes from the packages, and the business automation agents.

Run it. Read the SOUL files. Respect the gates. Ship small.
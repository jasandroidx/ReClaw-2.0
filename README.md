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

## Visual Agent Floor (Clawsmith Phase 1 - Committed to ravenstack)
Persistent multi-room "operating floor" per spec. Core compiler in `core/cell.py` (plain goal → CellBlueprint with prune for rural income, creates ~/.openclaw/workspace/rooms/<id>/ with SOUL.md/AGENTS.md/memory.db, Obsidian ForgePackage, visual WS events). 

- Rooms: Grant Hall Dungeon (purple_grant_watcher, funding tracker), Audit Chamber (red_auditor, compliance), Job Den, Research Lab, Content Studio, Marketplace Forge.
- Dashboard: `dashboard/index.html` (2D pixel grid, static desk-anchored hooded sprites with states idle/typing/glowing/success/error, neon CSS, WS to gateway:18789, Tailscale accessible on 8080 via new docker service). Click sprites to simulate.
- Revenue loops wired: grant alerts ($49/mo), compliance reports ($199), job leads ($29/mo), arbitrage feed ($19/mo), faceless YT content (ads/affiliates), dashboard as SaaS.
- Test: `python3 -m core.cell "Activate Grant Hall..."` (creates room, inits Total-ReClaw, emits event). `docker-compose up reclaw-dashboard` for visual.
- Sprite states and themes match pixel RPG reference (cozy, no pathfinding).

See AGENTS.md for Clawforge routing, core/cell.py for lifecycle, plan.md for full architecture.

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
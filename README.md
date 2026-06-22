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

## Ravenstack Fortress Dashboard (pixel office RPG from agent-town repo)

**Full interactive pixel RPG office/hall** (adapted from https://github.com/geezerrrr/agent-town) running at http://localhost:8080. You play as the Ravenlord walking the mystical stone/neon fortress. Assign tasks face-to-face to pixel agents in the 3 chambers (Clawforge blacksmith with hammer animations/sparks, Grant Hall scribe, Knowledge Vault archivist with lantern/glow). Real-time status, emotes, pathfinding, interaction menus (press E), HUD panels for workers/tasks/chat. Perfect OpenClaw integration via WS gateway on 18789. Our 3 skills (obsidian-ravenstack-ingest, clawhub-publish-cell for income bundles/video scripts, visual-fortress-e2e) are tied in via task assignment and docs.

**How to open it:**
- Navigate to **http://localhost:8080** (or Tailscale IP:8080)
- **Hard refresh (Ctrl+Shift+R)** or use incognito to load latest.
- Controls: Arrow keys/WASD to walk, E to interact near agents or Ravenlord spots. Use HUD for quick tasks, skills, logs.
- Live with our ReClaw cell.py event bus.

**One-command rebuild** (now uses the mature pixel office repo):
```bash
cd /root/ReClaw-2.0 && ./tools/rebuild-fortress-dashboard.sh
```
(or `/fortress-dashboard rebuild` skill). It kills old servers, starts npx @geezerrrr/agent-town tuned to our gateway/port, updates PID/log/docs.

Old Canvas/HTML and React Station House versions archived. This is production-grade, expandable (add rooms via map/tile edits), and directly supports income loops via ClawHub publish and Obsidian sync. Updated RAVENSTACK-ARCHITECTURE.md, skills, and rebuild script. Verified running with WS connected (see /tmp/dashboard_server.log and PID 2620445).

See agent-town components/game/scenes/OfficeScene.ts for core logic, our tweaks in globals.css (neon-purple/glow theme), README here, and vault for reload ritual. This resolves prior visual concerns by using a complete existing implementation tailored to OpenClaw/ReClaw.

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
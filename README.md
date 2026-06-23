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

## Knowledge Vault & Daily Document Ingest (Phase C)

**New in this update**: Dead-simple way to drop local PDFs, books, research papers, and knowledge files from your computer. kimi-claw extracts the best stuff, organizes it cleanly, and writes it to your Obsidian vault with frontmatter/tags. Instantly searchable in RAG + Fortress.

See the full guide: **[KNOWLEDGE_VAULT.md](KNOWLEDGE_VAULT.md)**

### Quickest Ways to Ingest Right Now

**RAG Dashboard** (easiest for most people)
- https://vb2sxll3shzgg.kimi.page
- Use **Import File** button or drag & drop

**Fortress Dashboard** (visual chambers)
- http://localhost:8080 (after rebuild)
- Knowledge Vault chamber → MCP ingest button

**CLI (batch/folder)**
```bash
cd /opt/reclaw
PYTHONPATH=. python3 -m core.cli ingest --file book.pdf --model kimi_claw
```

After uploading, run the reload ritual:
```bash
cd /opt/reclaw
PYTHONPATH=. python3 -m core.cell "Reload ritual"
```

## Quick Start (Local Python - Recommended for Testing)

This is the fastest way to test everything without Docker.

```bash
cp .env.example .env
# edit OBSIDIAN_VAULT_PATH to point at your vault

pip install -r requirements.txt

# Full end-to-end with seeds (safest)
python -m reclaw.cli run --county Pike --area Winslow
```

## Production on Hetzner (Docker + Tailscale)

See [docs/SETUP.md](docs/SETUP.md) and [docs/tailscale.md](docs/tailscale.md).

```bash
docker compose up -d
# Then hit the Gateway over Tailscale
```

**Note on Docker vs Local**: For daily document dropping and testing the Knowledge Vault, you can stay in local Python mode on the server. Docker is mainly for keeping the full system running 24/7 headless. Tailscale gives you easy remote access to the dashboards without opening public ports.

## Current Implementation (MVP rural_data module)
Core platform is domain-agnostic. This module demonstrates the patterns:
- **Researcher** (`agents/researcher/`) — pulls or loads seed data → ResearchPackage (JSON)
- **Analyst / Red Flag** (`agents/analyst/`) — turns research into insights + red flags + channel angles → AnalysisPackage
- **Light Orchestrator** — sequences them, enforces quality gates from SOUL, assembles ContentPackage, writes to Obsidian channel
- **Gateway** (`api/main.py`) — the control plane. Creates sessions, loads identities, manages permissions/approvals, exposes HTTP for triggers + status + future event feed.

See AGENTS.md for routing and core/platform capabilities. Future domains live in parallel under `agents/`.

## Key Folders

- `agents/<name>/SOUL.md` — identity loaded by every run of that agent (OpenClaw style)
- `core/handoff.py` — the strict JSON contract between agents (ResearchPackage, AnalysisPackage, ContentPackage)
- `core/security.py` — capability registry + approval gate implementation
- `core/session.py` — isolation: every run gets `data/sessions/<id>/` with souls, handoffs, approvals, logs
- `data/seeds/` — deterministic test data for Pike/Winslow (and future counties)
- `data/runs/` + `data/sessions/` — the full audit history
- `docs/SECURITY.md` — how the gates and Docker sandboxing work
- `docker-compose.yml` + `docker/Dockerfile` — GPU-ready, non-root, volume layout for Hetzner

## Ravenstack Fortress Dashboard (pixel office RPG)

**Full interactive pixel RPG office/hall** running at http://localhost:8080. You play as the Ravenlord walking the mystical stone/neon fortress. Assign tasks face-to-face to pixel agents in the 3 chambers (Clawforge, Grant Hall, Knowledge Vault). Real-time status via WS to gateway on 18789.

**One-command rebuild:**
```bash
cd /opt/reclaw/tools && bash rebuild-fortress-dashboard.sh
```

Hard refresh after rebuild. Controls: Arrow keys/WASD to walk, E to interact. HUD panels for tasks/logs.

## Status

MVP complete + Phase C Knowledge Vault ingest live.

Next: real live county fetchers, Scriptwriter agent, faceless channel episodes, business automation agents, and deeper integration of the visual dashboards.

Run it. Read the SOUL files. Respect the gates. Ship small.
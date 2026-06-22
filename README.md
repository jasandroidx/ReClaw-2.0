# ReClaw 2.0

**General-purpose agent operating platform** (OpenClaw-pattern aligned) with initial rural-data workflow module. A clean, production-grade foundation.

**Repo**: https://github.com/jasandroidx/ReClaw-2.0

**Current State (Cleanup Complete)**: Oracle (RAVENSTACK-ORACLE.md) is the single source of truth and queryable bible. MCP server (`core/oracle_mcp.py` + oracle skill) + ingestion pipeline (`scripts/ingest.py` with Groq distill per Oracle rules, canonical writes to /root/obsidian_vault/Ravenstack/, auto-git/reload). Dashboard (Ravenstack Fortress at :8080) has Oracle chamber (green chained eye sprite, MCP query buttons). All SOT enforced, stale cleaned, scripts reliable. Run `./scripts/verify.sh` for full check. Next phases: income (ClawHub cells, YT from rural data), full e2e, swarm agents.

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

<<<<<<< HEAD
=======
## Quick Start (Local)

```bash
cp .env.example .env
# edit OBSIDIAN_VAULT_PATH to point at your vault (/root/obsidian_vault/Ravenstack is canonical SOT per RAVENSTACK-ORACLE.md; outputs/obsidian for testing only)

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

>>>>>>> f87812ab (ravenstack fortress dashboard with oracle chamber, MCP buttons, sparks, ingest pipeline, verify, oracle bible, audit MD, SOT enforcement (local changes for ReClaw 2.0))
## Key Folders

- `knowledge/` — **Ravenstack**: The durable, distilled knowledge base (principles.md, agent-architecture.md, income-streams.md, etc.). Topic-based MD files. Central to all agents. See `knowledge/knowledge_index.md`.
- `agents/<name>/SOUL.md` — identity loaded by every run of that agent (OpenClaw style). Now references Ravenstack sections.
- `core/knowledge.py` — KnowledgeManager for targeted loading of Ravenstack files (prevents bloat).
- `core/handoff.py` — the strict JSON contract between agents (ResearchPackage, AnalysisPackage, ContentPackage)
- `core/security.py` — capability registry + approval gate implementation (extend for knowledge_read if needed)
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
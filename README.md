# ReClaw 2.0

**General-purpose agent operating platform** (OpenClaw-pattern aligned) with initial rural-data workflow module. A clean, production-grade foundation.

**Repo**: https://github.com/jasandroidx/ReClaw-2.0  
**Branch**: `ravenstack`  
**Production server**: `/root/ReClaw-2.0` on Hetzner (`178.156.235.36`)

> **📖 Full production reference:** [docs/PLATFORM-HANDBOOK.md](docs/PLATFORM-HANDBOOK.md) — everything wired, built, connected, and running on the server (ports, API, MCP, vault, RAG, Docker, ops cheat sheet).

ReClaw 2.0 provides a domain-agnostic core (Gateway, Session isolation, Security/approval gates, Obsidian durable memory, event model for future visual frontend). The current repo implements **rural_data** (county research, red-flag analysis, content packages) as the first concrete module. Future domains (grants, local_leads, content, research_packets, visual office) add cleanly under `agents/<domain>/` without changing core.

## Core Principles (from SOUL.md)

- Truth + provenance only. No hype.
- Least privilege + explicit approval gates for anything risky.
- Session isolation for every run (full audit trail on disk).
- Obsidian is the durable output + human review surface.
- Docker + Tailscale on Hetzner GPU box = prod. Local PC = identical dev mirror.
- Small, readable, extendable Python. No bloat.

## Stack (production)

| Service | Port | URL (tailnet) |
|---------|------|---------------|
| ReClaw API | 8000 | `https://openclaw.tail20a090.ts.net/reclaw/health` |
| OpenClaw gateway | 18789 | `https://openclaw.tail20a090.ts.net/health` |
| Fortress dashboard | 8081 | `http://127.0.0.1:8081` (local) |
| Ollama | 8080 | `http://127.0.0.1:8080` |
| MCP HTTP bridge | 8100 | `https://openclaw.tail20a090.ts.net/reclaw-mcp/mcp` |

See [docs/PLATFORM-HANDBOOK.md](docs/PLATFORM-HANDBOOK.md) for full architecture, MCP connectors, and ops commands.

## Knowledge Vault & Daily Document Ingest (Phase C)

Dead-simple way to drop PDFs, books, research papers, and knowledge files. Content is distilled, organized, and written to the Obsidian vault with frontmatter/tags. Instantly searchable in RAG + Fortress.

See: **[KNOWLEDGE_VAULT.md](KNOWLEDGE_VAULT.md)** and **[docs/rag/README.md](docs/rag/README.md)**

### Quickest ingest paths

**RAG API**
```bash
curl -X POST http://127.0.0.1:8000/rag/ingest \
  -H 'Content-Type: application/json' \
  -d '{"source_path": "/path/to/file.pdf"}'
```

**Fortress Dashboard** — http://127.0.0.1:8081 (Knowledge Vault chamber)

**CLI (batch/folder)**
```bash
cd /root/ReClaw-2.0
PYTHONPATH=. python3 scripts/ingest.py --file book.pdf
```

After uploading, sync RAG:
```bash
curl -X POST http://127.0.0.1:8000/rag/vault/sync
```

## Quick Start (Local Python)

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
cd /root/ReClaw-2.0
docker compose up -d
./scripts/post-deploy-healthcheck.sh
```

## Current Implementation (MVP rural_data module)

- **Researcher** (`agents/researcher.py`) — real Indiana public data (DOR, Gateway, salaries) → ResearchPackage
- **Analyst** (`agents/analyst.py`) — taxpayer red flags, multi-year budget shock → AnalysisPackage
- **Content Studio** (`agents/content_studio.py`) — 3 Shorts scripts from top flags → `short_scripts` in ContentPackage
- **Silent Auditor** (`agents/silent_auditor.py`) — compliance flags (optional; feeds Content Studio when present)
- **Orchestrator** — researcher → analyst → content studio → Obsidian (`pending_approval` scripts)
- **Gateway** (`api/main.py`) — sessions, permissions, HTTP triggers, RAG router
- **RAG** (`rag/`) — semantic search, vault sync, multi-format ingest

### Upload huge data files

```bash
scp ./export.csv root@178.156.235.36:/root/ReClaw-2.0/data/inbox/
ssh root@178.156.235.36 'cd /root/ReClaw-2.0 && PYTHONPATH=. python3 -c "from tools.inbox_loader import scan_inbox; scan_inbox()"'
```

See [AGENTS.md](AGENTS.md) for routing and [docs/HANDOFF.md](docs/HANDOFF.md) for JSON contracts.

## Key Folders

- `knowledge/` — Ravenstack knowledge base (principles, architecture, income streams)
- `agents/<name>/SOUL.md` — identity loaded per agent run
- `core/` — config, security, handoff, session, knowledge manager
- `rag/` — document ingestion + Chroma vector store
- `scripts/` — MCP servers, healthchecks, ingest pipeline
- `docs/` — setup, security, architecture, **PLATFORM-HANDBOOK**
- `data/sessions/` — per-run audit trail
- `data/inbox/` — drop zone for human-uploaded CSVs/PDFs (→ `ingestion/`)
- `data/cache/` — Gateway disbursement prefetch (2022–2025)
- `ingestion/` — real Pike budget, salary, anomaly CSVs

## Ravenstack Fortress Dashboard

Interactive pixel RPG office at **http://127.0.0.1:8081**. Walk the fortress, interact with agent chambers (Clawforge, Grant Hall, Knowledge Vault). Real-time status via WebSocket to gateway on 18789.

Controls: Arrow keys/WASD to walk, E to interact.

## Grok Build / MCP

Primary operator for server work. Unified connector: `reclaw-platform__*` (17 tools).  
Config: `~/.grok/config.toml` + `.grok/skills/reclaw-build/SKILL.md`

```bash
grok mcp doctor reclaw-platform
```

Details: [docs/PLATFORM-HANDBOOK.md §12](docs/PLATFORM-HANDBOOK.md#12-grok-build--mcp-connectors)

## Status

MVP complete + Phase C RAG + Kimi integration + MCP connectors live on server.

**Next:** live county fetchers, Scriptwriter agent, faceless channel episodes, full visual office swarm.

Run it. Read the SOUL files. Respect the gates. Ship small.
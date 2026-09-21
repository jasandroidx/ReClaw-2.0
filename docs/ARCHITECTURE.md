# ARCHITECTURE.md — ReClaw 2.0 Architecture Reference

## System Purpose

ReClaw 2.0 is an OpenClaw-aligned general-purpose agent operating platform. It provides a domain-agnostic foundation offering session isolation, security capability gates, durable memory in Obsidian, an event-driven status interface, and HTTP/MCP API triggers. Its initial domain application module is `rural_data` (Indiana county research, tax red-flag detection, local auditing, and script generation).

---

## Repository Component Map

- **Control Plane & Gateway API** (`api/main.py`)
  - Entry point for HTTP requests, trigger endpoints, county queue management, session initialization, and RAG routing.
- **Core Platform Runtime** (`core/`)
  - `core/config.py`: Configuration management via Pydantic Settings.
  - `core/session.py`: Session creation and disk-backed isolation (`data/sessions/`).
  - `core/security.py`: Central Capability registry, risk level enforcement, and session approval gate tracking.
  - `core/handoff.py`: Handoff and state schemas.
  - `core/job_registry.py`: Crash-safe JSON job state persistence.
  - `core/obsidian_writer.py`: Markdown and JSON package writer targeting configured Obsidian vault directories.
  - `core/fs_utils.py`: High-performance filesystem operations using `os.scandir()`.
  - `core/mcp_connector.py` / `core/oracle_mcp.py`: MCP integration interfaces.
- **Domain Module — Rural Data Swarm** (`agents/`)
  - `agents/researcher.py`: Public data gatherer (reads seeds and handles optional live HTTP fetches).
  - `agents/analyst.py`: Deterministic red-flag analysis and budget shock calculations.
  - `agents/content_studio.py`: Short script generator for local government findings.
  - `tools/local_auditor_live.py` / `tools/scriptwriter.py`: Specialized analysis and content generation utilities.
  - `core/county_queue.py`: County worklist cursor and review pipeline controller.
- **RAG & Knowledge System** (`rag/`, `knowledge/`)
  - `rag/`: Document chunking, embedding generation, Chroma vector storage, and vault sync.
  - `knowledge/`: Project knowledge base files (`RAVENSTACK-ORACLE.md`, `RAVENSTACK-ARCHITECTURE.md`, etc.).
- **Fortress Dashboard UI** (`dashboard/`)
  - Static HTML/JS frontend served via Python `http.server` (port 8081).
- **MCP Servers & Scripts** (`scripts/`)
  - `scripts/reclaw_platform_mcp_server.py`: Platform FastMCP server exposing tool integrations.
  - `scripts/ingest.py`: Document ingestion pipeline CLI.
  - `scripts/watchdog.py`: Process and service monitoring script.
- **CLI Utilities** (`cli.py`, `cli/`)
  - Command-line runner (`python -m reclaw.cli`).

---

## Entry Points

1. **HTTP Gateway API** (`api/main.py`)
   - Running via Uvicorn: `uvicorn api.main:app --host 0.0.0.0 --port 8000`.
   - Key routes: `/health`, `/trigger/{county}`, `/county-queue/*`, `/rag/*`.
2. **CLI Interface** (`cli.py`)
   - Command: `python -m reclaw.cli run --county <County> --area <Area>`.
3. **MCP Interface** (`scripts/reclaw_platform_mcp_server.py`)
   - FastMCP server listening on port 8100 (or stdin/stdout depending on runner).
4. **Fortress Dashboard Web Server** (`dashboard/`)
   - Static file server: `python3 -m http.server 8080 --directory dashboard` (mapped to port 8081).

---

## Runtime Components

- **Python Runtime**: Python 3.11/3.12 executing FastAPI, PyDantic, ChromaDB, and FastMCP.
- **FileSystem Memory**: Session JSON files under `data/sessions/`, run outputs in `data/runs/`, and vault output in `outputs/obsidian/` or configured vault path.
- **ChromaDB Vector Database**: Persisted on disk at `data/rag_chroma`.

---

## Docker / Container Components

`CONFIRMED FROM REPOSITORY` (`docker-compose.yml`, `docker/Dockerfile`):
- `openclaw-gateway`: Container running official OpenClaw image (`ghcr.io/openclaw/openclaw:2026.7.1`). Binds `127.0.0.1:18789:18789`. Maps host `./data` and `~/.openclaw`.
- `reclaw-api`: Custom Docker image built from `docker/Dockerfile` (Python 3.11-slim). Binds port `8000:8000`. Runs `uvicorn api.main:app`.
- `reclaw-dashboard`: Container running `python:3.12-slim` executing `python3 -m http.server 8080`. Binds host port `8081:8080`.

---

## External Integrations & Data Sources

- **Public Data APIs / Scraping**: Indiana Gateway, DOR, USASpending, ProPublica, Census API (`CENSUS_API_KEY`), Firecrawl (`FIRECRAWL_API_KEY`).
- **Obsidian Vault**: Target directory for final markdown analysis packages (`RECLAW_OBSIDIAN_VAULT_PATH`).
- **Tailscale**: Tailnet access layer providing HTTPS exposure for API and gateway endpoints (`CONFIRMED FROM REPOSITORY` via configuration and documentation).

---

## Agent / Model / Provider Integrations

- **Inference Strategy**:
  - `CONFIRMED FROM REPOSITORY`: `core/config.py` sets `enable_llm_analysis=False` by default; analysis defaults to deterministic heuristic rules. `LLM_MODEL` defaults to `llama3.1:8b` via Ollama when enabled.
  - `LIVE ENVIRONMENT NOTE`: Current production Hetzner host is CPU-only (~30 GB RAM). Secondary VM is CPU-only (~15.6 GiB RAM) and serves as small-model/emergency fallback host (e.g. Qwen 4B-class). Cloud providers are disabled by default.

---

## Tool / MCP Boundaries

- `core/security.py` defines the capability model (`DECLARED_CAPABILITIES`).
- Low-risk capabilities (`public_data_seed`, `heuristic_analysis`, `script_generate`, `visual_event_emit`) are granted automatically.
- Medium/High-risk capabilities (`public_data_live_fetch`, `obsidian_write`, `compliance_audit`, `shell_exec`) require session grants or approval records in `data/sessions/<session_id>/approvals/`.
- MCP server (`scripts/reclaw_platform_mcp_server.py`) operates as a tool connector subject to application capability constraints.

---

## Data-Flow Diagram (Plain Text)

```
[ HTTP Trigger / CLI / MCP ]
           │
           ▼
   [ Gateway API (api/main.py) ]
           │
           ├─► Creates Session & SecurityManager (data/sessions/<session_id>/)
           │
           ▼
   [ Orchestrator / Swarm Runner ]
           │
           ├─► 1. Researcher (agents/researcher.py)
           │      └─► Reads Seeds (data/seeds/) or Live HTTP (gated)
           │      └─► Writes researcher.json
           │
           ├─► 2. Local Auditor (tools/local_auditor_live.py)
           │      └─► Multi-source check (USASpending, Gateway, Census)
           │      └─► Writes silent_auditor.json
           │
           ├─► 3. Analyst (agents/analyst.py)
           │      └─► Heuristic red-flag analysis / budget shock evaluation
           │      └─► Writes analyst.json
           │
           ├─► 4. Content Studio (agents/content_studio.py)
           │      └─► Generates short scripts from red flags
           │      └─► Writes content_studio.json
           │
           ▼
   [ ObsidianWriter (core/obsidian_writer.py) ]
           │
           └─► Writes final .md + .json sidecar to RECLAW_OBSIDIAN_VAULT_PATH
```

---

## Network-Boundary Diagram (Plain Text)

```
[ External User / Tailscale Client ]
                 │
                 ▼
     [ Tailscale Interface / Host ]
                 │
  ┌──────────────┼──────────────────────────────┐
  │              │                              │
  ▼              ▼                              ▼
[reclaw-api]  [openclaw-gateway]     [reclaw-dashboard]
Port 8000     Port 18789 (127.0.0.1) Port 8081 (Host) -> 8080 (Container)
  │              │                              │
  └──────────────┴──────────────┬───────────────┘
                                │
                                ▼
                   [ Host Local Processes ]
                   ├─ Ollama (Port 8080 / 127.0.0.1) `LIVE ENVIRONMENT NOTE`
                   └─ ReClaw MCP Bridge (Port 8100 / host-gateway)
```

---

## Confirmed vs. Unconfirmed Architecture

### Confirmed from Repository
- Structure of core platform modules (`core/`), agents (`agents/`), and API routes (`api/main.py`).
- Docker Compose service definitions for `openclaw-gateway`, `reclaw-api`, and `reclaw-dashboard`.
- Capability security model (`core/security.py`).
- RAG architecture utilizing ChromaDB (`rag/`).

### Live Environment Notes (Unconfirmed by repository static files alone)
- Hetzner server specs (CPU-only, ~30 GB RAM).
- Secondary VM specs (CPU-only, ~15.6 GiB RAM).
- Exact active systemd daemon states (e.g. `reclaw-platform-mcp.service`).
- Tailscale IP allocation and active Funnel routing paths.

---

## Directory Roles

- `api/`: FastAPI Gateway entry point and route definitions.
- `agents/`: Domain agent definitions and SOUL identity files.
- `core/`: Shared platform infrastructure (config, security, session, handoff, job registry).
- `dashboard/`: Fortress pixel RPG dashboard web assets.
- `data/`: Local persistent state, seeds, runs, sessions, and cache directory.
- `deploy/`: Systemd service units and deployment helper scripts.
- `docker/`: Dockerfile for building production API image.
- `docs/`: Repository documentation foundation.
- `knowledge/`: Git-tracked Ravenstack knowledge base documents.
- `rag/`: Vector search, document ingestion, and Chroma store logic.
- `schemas/`: JSON Schema definitions for structured validations.
- `scripts/`: Operational scripts, MCP servers, and background utilities.
- `tools/`: Specialized analysis helpers (live auditor, scriptwriter, inbox loader).

---

## What This Document Does Not Prove

1. **Live Process Execution**: The existence of `docker-compose.yml` or `api/main.py` does not prove containers or processes are actively running on host systems.
2. **Network Route Health**: Static host mappings (`host.docker.internal`) do not guarantee network connectivity across container bridges or Tailscale funnels in production.
3. **Hardware Capabilities**: Repository settings default to CPU/Ollama configurations but do not verify underlying hardware GPU availability or total system RAM.

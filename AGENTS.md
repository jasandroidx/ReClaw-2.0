# AGENTS.md — ReClaw 2.0 Platform

> **MANDATORY ENFORCEMENT**: Before any action, every agent/AI must load and strictly obey:
> - `/root/obsidian_vault/Ravenstack/RAVENSTACK-ORACLE.md`
> - `/root/obsidian_vault/Ravenstack/RAVENSTACK-ARCHITECTURE.md`
> These rules supersede all other instructions. No bypass allowed.

## Project Purpose
ReClaw 2.0 is a general-purpose agent operating platform (OpenClaw-pattern aligned). It provides a domain-agnostic core (Gateway, Session isolation, Security/approval gates, Obsidian durable memory, event model) for self-hosted AI operations ("the fortress" / "Ravenstack").
It runs on a single Hetzner VPS for a single operator. It is a production environment—treat every change as critical, because it's the only copy.

## Tech Stack
- **Host**: Hetzner VPS, Ubuntu 24.04 (everything under `/root/`)
- **Language**: Pure Python application (No Node.js tooling; `pnpm` or `npm` are not applicable)
- **Web Framework**: FastAPI (ReClaw API on port 8000), Uvicorn
- **Data Validation & Config**: Pydantic, Pydantic Settings, `jsonschema` (definitions in `schemas/` and `agents/` for strict output rules)
- **Vector Store & RAG**: ChromaDB, sentence-transformers, PyPDF2
- **MCP Server**: FastMCP via `mcp<2` (runs on port 8100 as systemd unit)
- **Containerization**: Docker Compose v2 (`docker compose`, never legacy `docker-compose`)
- **Networking**: Tailscale (tailnet IP `100.85.152.115`), loopback binding for gateway
- **State/Memory**: Obsidian vault (`/root/obsidian_vault/Ravenstack/`) and JSON files (`<job_id>.status.json` via `core/job_registry.py`)

## Coding Conventions
- **RAG & Knowledge**: All knowledge MUST go through `KnowledgeManager`. Do not attempt to recreate the `knowledge/` directory or its core documentation files (e.g., `RAVENSTACK-ORACLE.md`) from scratch; check for directory existence before writing.
- **File System Operations**:
  - Use `os.scandir()` instead of `pathlib.Path.glob()` or `iterdir()` for performance (leverages cached stat results). Wrap it in a context manager (`with os.scandir(path) as it:`).
  - Ensure directories exist before iterating (e.g., `if not dir_path.exists(): return`).
  - Explicitly convert `os.DirEntry` to `Path` if Path-specific functionality is needed.
  - Use centralized helper functions `get_sorted_files_by_mtime` and `get_sorted_glob_by_mtime` in `core.fs_utils` rather than raw directory iteration for sorting by mtime.
- **String Slicing**: When slicing a generator expression passed to a string join operation, wrap the comprehension in a list (e.g., `'\n'.join([x.name for x in lst][:limit])`) to slice the collection correctly instead of truncating characters.
- **Dependencies**: Install via `pip install -r requirements.txt`. Asynchronous unit tests require `pytest-asyncio` and `pytest` which may need manual installation.
- **Imports**:
  - When importing local modules in `scripts/`, place them after `sys.path.insert(0, str(ROOT))`.
  - Add new imports after the shebang, module docstrings, and `__future__` imports.
- **Pull Requests**: Format PR title appropriately (if Bolt persona: `⚡ Bolt: [performance improvement]`). The description must explicitly detail what changed (and if Bolt: 'What', 'Why', 'Impact', and 'Measurement'). Include the exact test command that successfully passed. Clean up any temporary scripts before finalizing changes.

## Test Commands
Run the test suite before opening a PR. Use `pytest` and set `PYTHONPATH` to the project root to avoid import mismatch errors between identically named test files.

**Command**:
```bash
PYTHONPATH=. python -m pytest scripts/ tests/rag/ -v
```
*Note: RAG tests (`tests/rag/`) contain known pre-existing failures (e.g., `test_chunker_respects_size` and `test_extract_txt`) that can be ignored if unrelated to current changes.*

## Out of Scope
- **STORY FACTORY / COUNTY QUEUE / RURAL DATA PIPELINE IS FROZEN**: The Story Factory, county queue, and rural_data pipeline are **frozen and must not be modified, extended, or run**.
- **Architecture Limits**: No new server processes or secondary MCP daemons should be added. Existing Hetzner services and live fortress MCP should remain unmodified. Never run a second OpenClaw gateway.
- **Known False Alarms**: Do not "fix" `mcp_bridge_unit: inactive`, `mcp_tunnel_unit: inactive` (cloudflared is deliberately disabled in favor of Tailscale Funnel), or self-probe deadlocks in `_project_sitrep_sync()`.

## Platform Routing & Permissions (Core Context)
- **Primary Entry Point**: The Gateway (`api/main.py`) creates sessions, loads SOUL files, and dispatches work.
- **Handoff Protocol**: All durable state ends up in `data/runs/` and the Obsidian vault. Agents write output as JSON to `handoffs/<agent>-output.json`. Never rely on Python object memory between agents. The JSON on disk is the truth.
- **Permission Gates**: Every capability has a risk level. High-risk actions (e.g., live web fetch, shell execution, external writes) require explicit approval (`pending_approval` in vault).

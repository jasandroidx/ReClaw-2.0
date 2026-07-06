# ReClaw 2.0 MCP Status

Last updated: 2026-07-06

## Overview

The MCP layer is a consolidated async connector engine with schema validation, cost gating, secret scrubbing, WAL logging, and orchestration. Entry point: `core/oracle_mcp.py` singleton `mcp`.

**Overall health:** 88.5 / 100 — **healthy** (3 connectors degraded)

## Connectors (13)

| Connector | Status | Notes |
|-----------|--------|-------|
| `github` | OK | Search, issues, file content, comments |
| `llm` | OK | Grok primary; Perplexity/Gemini if keys set |
| `hetzner` | OK | Server list/get |
| `notion` | OK | Search, get_page |
| `obsidian` | OK | Vault search/read/write (local) |
| `tailscale` | OK | status, whoami, ping, peers |
| `docker` | OK | ps, compose_ps, logs |
| `ollama` | OK | Local API `http://localhost:11434` |
| `huggingface` | OK | Model search |
| `reclaw_meta` | OK | Introspection + health scoring |
| `gmail` | Degraded | Needs Google OAuth token |
| `google_drive` | Degraded | Needs Google OAuth token |
| `canva` | Degraded | Needs Canva Connect OAuth app |

## What's Working

- **Grok (xAI)** — live LLM calls
- **Gemini** — API key configured for LLM routing
- **GitHub** — PAT configured; repo search and API actions
- **Hetzner** — API token; server inventory
- **Notion** — integration token; search API
- **Obsidian** — direct Ravenstack vault access
- **Tailscale / Docker** — local CLI read-only
- **Ollama** — local daemon on port 11434 (`OLLAMA_API_BASE`)
- **HuggingFace** — token configured
- **Orchestration** — `quick_health`, `auto_heal_docker`, `smart_research`, handoffs, phone shortcuts
- **CLI** — `cli/mcp_cli.py`

## What's Degraded / Paused

- **Gmail + Google Drive** — OAuth client JSON saved at `credentials/.credentials.json`; token not completed. Finish with `python scripts/google_oauth_setup.py --auto` when ready.
- **Canva** — placeholder; requires Canva Connect OAuth
- **Perplexity** — no key; LLM falls back to stub for Perplexity routing

## Key Files

| Path | Purpose |
|------|---------|
| `core/mcp_connector.py` | Connector ABC, registry, 13 implementations |
| `core/oracle_mcp.py` | Singleton orchestrator, gating, WAL, orchestration |
| `core/google_oauth.py` | Google token helper (Gmail/Drive) |
| `core/security.py` | `MCP_READ_ONLY` capability set |
| `cli/mcp_cli.py` | Operator CLI |
| `scripts/google_oauth_setup.py` | Google OAuth setup (`--auto` for no copy/paste) |
| `credentials/.credentials.json` | Google OAuth client secrets |
| `credentials/google_token.json` | Google access token (after OAuth) |
| `data/mcp_logs/` | Daily JSONL execution logs |
| `data/mcp_queue.jsonl` | WAL queue |
| `Ravenstack/mcp-audit/` | Obsidian audit drain |

## Architecture Notes

- **Async-first** — `await mcp.query(...)`; sync wrappers `*_sync()` for CLI/scripts
- **Schema validation** — `actions_schema` per connector; params checked pre-execution
- **Cost gating** — `MAX_MCP_DAILY_BUDGET` (default $2.00/day)
- **Secret scrubbing** — tokens redacted before logging
- **Legacy compat** — `query_oracle`, `ingest_document` shims for `scripts/ingest.py`

## CLI Usage

```bash
cd /root/ReClaw-2.0
.venv/bin/python cli/mcp_cli.py status
.venv/bin/python cli/mcp_cli.py health
.venv/bin/python cli/mcp_cli.py connectors
.venv/bin/python cli/mcp_cli.py heal_docker
.venv/bin/python cli/mcp_cli.py meta overall_health
.venv/bin/python cli/mcp_cli.py query github search q=ReClaw-2.0
```

## Recommended Next Steps

1. Finish Google OAuth (`--auto` flow) for Gmail + Drive
2. Add `PERPLEXITY_API_KEY` if smart research routing to Perplexity is wanted
3. Wire MCP as OpenClaw gateway tools (stdio/SSE server)
4. Optional: Canva Connect OAuth when design automation is needed
5. Optional: real docker restart in `auto_heal_docker` (currently log/recommend only)
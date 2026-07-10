# ReClaw 2.0 MCP Status

**Last Updated:** 2026-07-06

## Current State
- Unified MCP connector layer is operational
- 13 connectors registered
- Core is async with schema validation and structured logging
- Health: ~88.5/100 (3 connectors degraded: Gmail, Google Drive, Canva due to OAuth/token issues)
- Logging enabled in `data/mcp_logs/`
- Basic orchestration + handoffs in place
- CLI available at `cli/mcp_cli.py`

## What's Working Well
- GitHub, LLM (Grok primary + Perplexity + Gemini), Hetzner, Docker, Tailscale, Ollama, Hugging Face, Notion, Obsidian, ReClawMeta
- Error handling + retries
- Health scoring and quick status
- Structured logging of all MCP actions

## What's Degraded / Needs Work
- Gmail, Google Drive, Canva (OAuth/token setup incomplete)
- Self-healing is still mostly logging + recommendations (not fully automatic yet)
- CLI works but needs to be run from project root (or use the patched version)

## Key Files
- `core/mcp_connector.py` — Connector ABC + registry
- `core/oracle_mcp.py` — Main orchestration + query layer
- `cli/mcp_cli.py` — Command line interface
- `data/mcp_logs/` — Daily structured logs

## Recommended Next Steps
1. Finish Gmail + Google Drive OAuth setup
2. Improve self-healing (make it actually restart containers when safe)
3. Expand CLI with more useful commands
4. Add automated backups for the ReClaw folder
5. Continue building agent orchestration on top of MCP

## Grok Chat Connector

**Last verified:** 2026-07-10 — bridge + cloudflared live.

| Plane | Endpoint |
|-------|----------|
| Public | `data/mcp_public_url.txt` → e.g. `https://locate-retailer-dana-les.trycloudflare.com/mcp` |
| Tailscale | `http://100.108.130.82:8100/mcp` · `…/health` |
| Knowledge | Vault `Ravenstack/mcp-connector.md` + ORACLE MCP section |

**Chat:** *"use ravenstack connector to [tool]"* → `reclaw-platform__*` / `ravenstack__*` (17+ tools).

**Grok Build (this server):** `reclaw-mcp` + `reclaw-platform` in `/root/.grok/config.toml`.

**SuperGrok (grok.com):** [grok.com/connectors](https://grok.com/connectors) → Custom → URL from `data/mcp_public_url.txt` (cloudflared tunnel, MCP-only).

**Tailscale (phone/laptop):** `https://openclaw.tail20a090.ts.net/reclaw-mcp/mcp`

**OpenClaw agents:** `openclaw mcp list` → `reclaw-platform` (17 tools), `reclaw-mcp` (8 tools).

Blocked at `reclaw-mcp` bridge: `github.create_comment`, `obsidian.write`. LLM queries respect `MAX_MCP_DAILY_BUDGET`.

## Safety
- Project is now under git
- Backup script exists at `backup-reclaw.sh`
- Logging + health checks provide good visibility
- MCP Grok bridge is read-first; writes blocked at server boundary

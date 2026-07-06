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

Safe MCP bridge: `scripts/reclaw_mcp_server.py` (Grok Build tools: `reclaw-mcp__*`)

```toml
# ~/.grok/config.toml
[mcp_servers.reclaw-mcp]
command = "ssh"
args = ["root@YOUR_HOST", "/root/ReClaw-2.0/.venv/bin/python", "/root/ReClaw-2.0/scripts/reclaw_mcp_server.py"]
```

Blocked at bridge: `github.create_comment`, `obsidian.write`. LLM queries respect `MAX_MCP_DAILY_BUDGET`.

## Safety
- Project is now under git
- Backup script exists at `backup-reclaw.sh`
- Logging + health checks provide good visibility
- MCP Grok bridge is read-first; writes blocked at server boundary

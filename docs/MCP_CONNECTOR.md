# Ravenstack / ReClaw Platform MCP Connector

**Last verified:** 2026-07-10  
**Vault SOT (full map):** `/root/obsidian_vault/Ravenstack/mcp-connector.md` + ORACLE section **MCP Connector**  
**Process:** `scripts/reclaw_platform_mcp_server.py` (FastMCP name: `reclaw-platform`)

## What it is

One MCP server so agents can **see and change** the stack in real time: vault R/W, RAG/ORACLE, rural_data pipeline, Docker/git/health. **17 tools**. Prefer MCP over raw shell for these actions.

Chat trigger: **"use ravenstack connector to [tool]"** → call `reclaw-platform__*` or `ravenstack__*`.

## How it operates

```
Client (Grok Build / grok.com / Tailnet device)
  → stdio  OR  streamable-http :8100
  → reclaw_platform_mcp_server.py
  → KnowledgeManager / RAG / vault FS / ReClaw API :8000 / OpenClaw / docker / git
```

| Layer | Detail |
|-------|--------|
| Bridge | systemd `reclaw-mcp-bridge` → `scripts/run-reclaw-mcp-bridge.sh` |
| Public tunnel | systemd `reclaw-mcp-tunnel` → cloudflared → `http://127.0.0.1:8100` |
| Public URL SOT | `data/mcp_public_url.txt` (**gitignored**; hostnames rotate) |
| Tunnel host allowlist | `data/mcp_tunnel_host.txt` (gitignored) |

## Live endpoints

| Plane | Endpoint | Audience |
|-------|----------|----------|
| **stdio** | Grok Build on Hetzner | Best local operator path |
| **Tailscale** | `http://100.108.130.82:8100/mcp` · health `…/health` | Tailnet only |
| **Public** | Read `data/mcp_public_url.txt` (must end `/mcp`) | grok.com Custom Connector |

Health JSON example:

```json
{"status":"ok","service":"reclaw-platform","transport":"streamable-http","port":8100}
```

> trycloudflare quick-tunnel hostnames **rotate** when cloudflared restarts. Never hardcode a stale host as permanent truth — re-read the URL file.

## Tools (17)

| Group | Tools |
|-------|--------|
| Knowledge | `query_knowledge`, `read_oracle`, `list_knowledge_topics`, `ingest_to_ravenstack`, `save_ravenstack_note` |
| Vault / repo | `read_vault_file`, `write_vault_file`, `read_repo_file` |
| Pipeline | `reclaw_health`, `run_pike_winslow`, `rag_sync_vault`, `list_pipeline_sessions` |
| Ops | `stack_health`, `docker_status`, `openclaw_health`, `git_status`, `connector_help` |

## Security

| Rule | Detail |
|------|--------|
| **No HTTP auth** | Public tunnel URL ≈ secret. Do not paste into public issues. |
| Prefer Tailscale | Private daily remote use; Cloudflare only for clients off-tailnet (e.g. grok.com). |
| Path sandbox | Vault/repo tools cannot escape base directories. |
| Mutations | Writes + pipeline require **explicit user intent**. |
| Secrets | Env / OpenClaw secrets only — never vault notes or public chats. |

## Usage rules

1. Prefer MCP for vault, knowledge, pipeline, and health.
2. Reads: free. Writes / `run_pike_winslow`: only when the user asks.
3. Full sitrep: skill `ravenstack-sitrep` (multi-tool distilled report).
4. After knowledge edits: `reload_ritual` + vault git commit/push when durable.

## Ops commands

```bash
# Health
curl -sS http://100.108.130.82:8100/health

# Bridge / tunnel
systemctl status reclaw-mcp-bridge reclaw-mcp-tunnel
systemctl restart reclaw-mcp-bridge

# Public URL after tunnel restart
systemctl restart reclaw-mcp-tunnel
cat /root/ReClaw-2.0/data/mcp_public_url.txt

# Grok doctor
cd /root/ReClaw-2.0 && grok mcp doctor reclaw-platform   # expect 17 tools
```

## Client config sketches

**Grok Build (server):** stdio in `~/.grok/config.toml` → `[mcp_servers.reclaw-platform]`

**Tailnet device:**
```toml
[mcp_servers.reclaw-platform]
url = "http://100.108.130.82:8100/mcp"
```

**grok.com:** Custom Connector → URL from `data/mcp_public_url.txt`

## Related

- Vault: `Ravenstack/mcp-connector.md`, `RAVENSTACK-ORACLE.md` § MCP Connector
- Handbook: `docs/PLATFORM-HANDBOOK.md` §12
- Status: `docs/MCP_STATUS.md`
- Skill: `.grok/skills/ravenstack-sitrep/SKILL.md`

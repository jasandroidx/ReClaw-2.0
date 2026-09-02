# Ravenstack MCP Connector — Setup & Operating Map

**Purpose:** Single setup + ops guide for the ReClaw Platform / Ravenstack MCP — how it works, endpoints, security, usage rules, and client config.

**Last verified:** 2026-07-10  
**Vault SOT:** `/root/obsidian_vault/Ravenstack/mcp-connector.md` + ORACLE § MCP Connector  
**Repo mirror:** `docs/MCP_CONNECTOR.md`  
**Process:** `scripts/reclaw_platform_mcp_server.py` (FastMCP name: `reclaw-platform`)

---

## What it is

One MCP server so agents can **see and change** the stack in real time:

- Vault read/write
- RAG / ORACLE knowledge
- rural_data pipeline (`run_pike_winslow`)
- Docker / git / stack health

**19 tools** on `reclaw-platform`. Prefer MCP over raw shell for these actions.

**Chat trigger:** *"use ravenstack connector to [tool]"* → call `reclaw-platform__*` or `ravenstack__*`.

---

## Principles

1. **One connector, many faces** — Same process over **stdio** (Grok Build on Hetzner) or **streamable-http** (`:8100`).
2. **Live stack actions** — Prefer MCP for vault, knowledge, pipeline, health.
3. **Truth + provenance** — Distilled writes only; path-sandboxed FS; no inventing health.
4. **Two remote planes** — **Tailnet** (private) vs **public Cloudflare tunnel** (grok.com / internet). Never confuse them.
5. **Chat trigger** — *"use ravenstack connector to [tool]"* or *"use reclaw-platform [tool]"*.

---

## How it operates

```
Client (Grok Build / grok.com / Tailnet device)
  → stdio  OR  streamable-http :8100
  → reclaw_platform_mcp_server.py (FastMCP "reclaw-platform")
  → KnowledgeManager / RAG / vault FS / ReClaw API :8000 / OpenClaw :18789 / docker / git
```

| Layer | Detail |
|-------|--------|
| Bridge | systemd `reclaw-mcp-bridge` → `scripts/run-reclaw-mcp-bridge.sh` |
| Public tunnel | systemd `reclaw-mcp-tunnel` → cloudflared → `http://127.0.0.1:8100` |
| Public URL SOT | `data/mcp_public_url.txt` (**gitignored**; hostnames rotate) |
| Tunnel host allowlist | `data/mcp_tunnel_host.txt` (gitignored) |
| Tool count | **19** on `reclaw-platform` (+ `ravenstack__*`, `reclaw-api__*`, etc. on Grok Build) |
| Health probe | `GET /health` → `{"status":"ok","service":"reclaw-platform","transport":"streamable-http","port":8100}` |
| MCP path | Clients must use **`/mcp`** (not bare host) |

### Decision tree

```
Need stack action from chat?
  ├─ On Hetzner Grok Build → reclaw-platform__* or ravenstack__* (stdio)
  ├─ Client on Tailscale only → https://openclaw.tail20a090.ts.net:8100/mcp
  ├─ grok.com / public internet → URL in data/mcp_public_url.txt
  │     (current: https://openclaw.tail20a090.ts.net/rk7m2q9x/mcp)
  └─ Offline MCP → shell fallback (post-deploy-healthcheck, git, vault paths)

Read vs write?
  ├─ Read (health, query, read_*) → auto OK
  └─ Write (vault, ingest, pipeline) → human intent required; approval for high-risk
```

---

## Live endpoints (verified 2026-07-10)

| Plane | URL | Audience |
|-------|-----|----------|
| **Public tunnel (MCP)** | `https://openclaw.tail20a090.ts.net/rk7m2q9x/mcp` | grok.com Custom Connector, remote HTTPS |
| **Tailscale IP (MCP)** | `https://openclaw.tail20a090.ts.net:8100/mcp` | Tailnet devices only |
| **Tailscale health** | `https://openclaw.tail20a090.ts.net:8100/health` | Liveness JSON |
| **URL file (SOT for public)** | `/root/ReClaw-2.0/data/mcp_public_url.txt` | May change on tunnel restart |
| **Tunnel host file** | `/root/ReClaw-2.0/data/mcp_tunnel_host.txt` | DNS-rebinding allowlist |
| **stdio** | Grok Build on Hetzner | Best local operator path |

Health JSON example:

```json
{"status":"ok","service":"reclaw-platform","transport":"streamable-http","port":8100}
```

> **Warning:** Cloudflare quick tunnels **rotate hostnames** when `cloudflared` restarts. Always re-read `data/mcp_public_url.txt` before publishing a connector URL. Do not hardcode stale trycloudflare hosts as permanent.

---

## Tools (19 — reclaw-platform)

| Group | Tools |
|-------|--------|
| Knowledge | `query_knowledge`, `read_oracle`, `list_knowledge_topics`, `ingest_to_ravenstack`, `save_ravenstack_note` |
| Vault / repo | `read_vault_file`, `write_vault_file`, `read_repo_file` |
| Pipeline | `reclaw_health`, `run_pike_winslow`, `rag_sync_vault`, `list_pipeline_sessions`, `inspect_session`, `pipeline_status` |
| Ops | `stack_health`, `docker_status`, `openclaw_health`, `git_status`, `connector_help` |

Safe reads: `inspect_session` (validated id; distilled only) · `pipeline_status` (queue + packages + sessions).

On Grok Build, prefixes: `reclaw-platform__*` (primary) and `ravenstack__*` (overlap for Oracle/RAG/ops).

---

## Security

| Control | Status |
|---------|--------|
| **Auth on HTTP MCP** | **None today** — public tunnel = open tool surface. Treat URL as secret. |
| **Network split** | Bridge binds `0.0.0.0:8100` for local + TS; prefer Tailscale for private ops. Public only via cloudflared → localhost. |
| **DNS rebinding** | `MCP_PUBLIC_MODE=1` relaxes host checks for Cloudflare Host headers; allowlist includes TS IP + tunnel host. |
| **Path sandbox** | vault/repo tools cannot escape base dirs; escape → error. |
| **Gateway token** | `RECLAW_GATEWAY_TOKEN` attached when curling `127.0.0.1:8000` if set. |
| **Secrets** | Env / OpenClaw secrets only — never vault notes or public chats. |
| **Mutations** | Writes + pipeline require **explicit user intent**; high-risk follows approval gates. |
| **Least privilege** | Prefer read tools; no full shell via MCP. |

> Until HTTP auth exists: prefer **Tailscale** for daily remote use; use **Cloudflare** only for clients that cannot join the tailnet (e.g. grok.com). Do not put the trycloudflare URL in public GitHub issues.

### Red flags

| Severity | Flag | Action |
|----------|------|--------|
| **high** | Public tunnel URL shared in public chat/issues | Rotate tunnel; treat as credential |
| **high** | Unsolicited `write_vault_file` / `run_pike_winslow` | Refuse without explicit user ask |
| **medium** | Stale trycloudflare hostname in docs/config | Re-read `mcp_public_url.txt` |
| **medium** | Using Tailscale IP from non-tailnet client | Switch to Cloudflare URL or join tailnet |
| **medium** | Path traversal on vault/repo tools | Blocked by `_safe_path`; log + refuse |
| **low** | GET `/mcp` returns 4xx | Expected without MCP session — use MCP client |

---

## Usage rules

1. Prefer MCP for vault, knowledge, pipeline, and health.
2. Reads: free. Writes / `run_pike_winslow`: only when the user asks.
3. Full sitrep: skill `ravenstack-sitrep` (multi-tool distilled report).
4. After knowledge edits: `reload_ritual` + vault git commit/push when durable.

### Chat usage

| User says | Agent does |
|-----------|------------|
| use ravenstack connector to stack_health | `reclaw-platform__stack_health` or `ravenstack__stack_health` |
| use ravenstack connector to query [topic] | `query_knowledge` |
| use ravenstack connector to read oracle | `read_oracle` |
| use ravenstack connector to run pike | `run_pike_winslow` (confirm write_obsidian) |
| sitrep / fortress status | skill `ravenstack-sitrep` |

---

## Client setup

### Grok Build (on this server — best)

```toml
# ~/.grok/config.toml or /root/ReClaw-2.0/.grok/config.toml
[mcp_servers.reclaw-platform]
command = "/root/ReClaw-2.0/.venv/bin/python"
args = ["/root/ReClaw-2.0/scripts/reclaw_platform_mcp_server.py"]
# tools appear as reclaw-platform__*
```

### Tailnet device

```toml
[mcp_servers.reclaw-platform]
url = "https://openclaw.tail20a090.ts.net:8100/mcp"
```

### grok.com Custom Connector

1. Ensure bridge + tunnel: `systemctl status reclaw-mcp-bridge reclaw-mcp-tunnel`
2. URL = contents of `data/mcp_public_url.txt` (must end with `/mcp`)
3. Name: `ReClaw Platform` / `Ravenstack`
4. Test: *"use ravenstack connector to stack_health"*

### SSH stdio (remote CLI clients)

```bash
ssh root@178.156.235.36 '/root/ReClaw-2.0/.venv/bin/python /root/ReClaw-2.0/scripts/reclaw_platform_mcp_server.py'
```

---

## Ops commands

```bash
cd /root/ReClaw-2.0

# Health
curl -sS https://openclaw.tail20a090.ts.net:8100/health
curl -sS http://127.0.0.1:8100/health

# Bridge / tunnel
systemctl status reclaw-mcp-bridge reclaw-mcp-tunnel
systemctl restart reclaw-mcp-bridge

# Public URL after tunnel restart (hostnames rotate)
systemctl restart reclaw-mcp-tunnel
cat data/mcp_public_url.txt

# Full stack check
./scripts/post-deploy-healthcheck.sh

# Grok doctor
grok mcp doctor reclaw-platform   # expect 17 tools

# Reload ritual after knowledge/structure changes
python3 -m core.cell "Reload structure - test fortress"
```

### Enable systemd units (if not already)

```bash
sudo cp deploy/reclaw-mcp-bridge.service /etc/systemd/system/
sudo cp deploy/reclaw-mcp-tunnel.service /etc/systemd/system/  # if present
sudo systemctl daemon-reload
sudo systemctl enable --now reclaw-mcp-bridge reclaw-mcp-tunnel
```

---

## Related paths

| Path | Role |
|------|------|
| `scripts/reclaw_platform_mcp_server.py` | Unified connector (17 tools) |
| `scripts/run-reclaw-mcp-bridge.sh` | HTTP bridge launcher |
| `scripts/run-mcp-public-tunnel.sh` | Cloudflare quick tunnel |
| `deploy/reclaw-mcp-bridge.service` | systemd unit |
| `data/mcp_public_url.txt` | Live public URL (gitignored) |
| `/root/obsidian_vault/Ravenstack/mcp-connector.md` | Vault full map |
| `docs/MCP_CONNECTOR.md` | Repo mirror |
| `docs/PLATFORM-HANDBOOK.md` §12 | Handbook |
| `.grok/skills/ravenstack-sitrep/SKILL.md` | Live sitrep skill |

---

## Sources & provenance

- Live process: `reclaw-mcp-bridge` + `cloudflared` (verified 2026-07-10)
- Operator endpoints: Cloudflare `locate-retailer-dana-les.trycloudflare.com/mcp` + Tailscale `100.108.130.82:8100`
- ORACLE / SOK / knowledge_index updated and vault-synced same day

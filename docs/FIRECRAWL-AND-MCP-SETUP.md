# Firecrawl + MCP Connector Setup (ReClaw 2.0)

Last updated: 2026-07-06. For the faceless county-auditor channel on Hetzner.

---

## 1. Firecrawl — what it is for (and what it is NOT for)

### Use Firecrawl (Tier 3 — discovery + context)

| Target | Why |
|--------|-----|
| County `.in.gov` sites | Meeting minutes, bid tabulations, press releases |
| `in.gov/dor` budget-order pages | Find PDF links per county |
| `in.gov/sboa` audit reports | Discover audit PDF URLs |
| Narrative provenance | "So what?" section in watchdog scripts |

### Do NOT use Firecrawl for (Tier 1 — already built)

| Target | Use instead |
|--------|-------------|
| Gateway disbursements | `tools/indiana_gateway.py` → flat file download |
| Gateway certified budgets | Same flat file |
| USASpending / Census / ProPublica | Live APIs in `tools/local_auditor_live.py` |

### Architecture

```
Tier 1  Gateway flat files + APIs     → red_flag_engine (math)
Tier 2  Playwright MCP                → Gateway salary export, Beacon GIS
Tier 3  Firecrawl                     → PDF/link discovery, county context
Tier 4  Human approval gate           → before publish
```

---

## 2. Install Firecrawl (server)

### Python SDK (pipeline code)

```bash
cd /root/ReClaw-2.0
.venv/bin/pip install firecrawl-py
```

Already wired: `tools/firecrawl_discovery.py`

### API key

1. Sign up: https://firecrawl.dev
2. Copy API key (`fc-...`)
3. Add to `/root/ReClaw-2.0/.env`:

```bash
FIRECRAWL_API_KEY=fc-your-key-here
```

4. Export for MCP (add to `~/.grok/config.toml` env or shell profile):

```bash
export FIRECRAWL_API_KEY=fc-your-key-here
```

### Test discovery

```bash
cd /root/ReClaw-2.0
export FIRECRAWL_API_KEY=fc-your-key
PYTHONPATH=. .venv/bin/python -c "
from tools.firecrawl_discovery import discover_county_context
print(discover_county_context('Pike'))
"
```

Output cache: `data/cache/firecrawl/pike_discovery.json`

### Firecrawl MCP (for the agent in chat)

Add to `~/.grok/config.toml`:

```toml
[mcp_servers.firecrawl]
command = "npx"
args = ["-y", "firecrawl-mcp"]
startup_timeout_sec = 60

[mcp_servers.firecrawl.env]
FIRECRAWL_API_KEY = "${FIRECRAWL_API_KEY}"
```

Verify:

```bash
grok mcp doctor firecrawl
```

**Note:** The marketplace `firecrawl` HTTP plugin (`https://mcp.firecrawl.dev/v2/mcp`) may require OAuth in Grok — prefer the **stdio `npx firecrawl-mcp`** config above when you have an API key.

---

## 3. MCP status on this server (2026-07-06)

Run anytime:

```bash
grok mcp doctor
grok mcp doctor reclaw-platform
grok mcp doctor obsidian
```

| Server | Status | Action needed |
|--------|--------|---------------|
| **reclaw-platform** | ✅ Healthy (17 tools) | None — **use this first** |
| **ravenstack** | ✅ Healthy (12 tools) | None |
| **reclaw-api** | ✅ Healthy | None |
| **reclaw-fs** | ✅ Healthy (14 tools) | None — direct vault/repo file access |
| **github** | ✅ Healthy (91 tools) | Needs `GITHUB_TOKEN` in env |
| **grok_com_canva** | ✅ Healthy (33 tools) | OAuth via Grok — for thumbnails/Shorts visuals |
| **grok_com_notion** | ✅ Healthy (20 tools) | OAuth via Grok |
| **obsidian** | ❌ Failing | **Wrong config** — see §4 |
| **playwright** | ⏸ Disabled | Enable — see §5 |
| **firecrawl** | ⚠️ Plugin OAuth fail | Add stdio config + API key — see §2 |
| **brave-search** | ⏸ Disabled | Optional — needs `BRAVE_API_KEY` |
| **reclaw-platform-remote** | ⏸ Disabled | Tailscale remote MCP — enable if needed |

---

## 4. Obsidian MCP — why it fails and what to use instead

### The problem

`obsidian-mcp-server` (cyanheads) does **not** read vault files directly. It talks to the **Obsidian desktop app** via the **Local REST API** community plugin:

- Requires `OBSIDIAN_API_KEY` (from Obsidian → Settings → Local REST API)
- Requires Obsidian app **running** on the machine at `http://127.0.0.1:27123`

Your vault lives on **Hetzner** (`/root/obsidian_vault`). Obsidian desktop runs on **your Windows PC**. The current config only sets `OBSIDIAN_VAULT_PATH` — that is **wrong** for this MCP server.

### What works TODAY (no Obsidian app on server)

| Need | Use |
|------|-----|
| Read/write vault files | `reclaw-platform__read_vault_file` / `write_vault_file` |
| Read/write repo files | `reclaw-fs` or `reclaw-platform__read_repo_file` |
| Pipeline → vault MD | `curl -X POST 'http://127.0.0.1:8000/run-sync?...&write_obsidian=true'` |

### If you want obsidian MCP working

**Option A — Obsidian on your PC (recommended for editing)**

1. Install [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) plugin in Obsidian
2. Enable HTTP server, copy API key
3. Sync vault to PC (Syncthing/git) OR use Remote Tunnel
4. Point MCP at your PC's REST API (only works when Cursor/Grok runs locally)

**Option B — Keep server headless (current setup)**

Disable broken obsidian MCP; use reclaw-platform vault tools:

```toml
[mcp_servers.obsidian]
enabled = false
```

---

## 5. Playwright MCP — enable for Gateway salary + Beacon GIS

Playwright is **disabled** in config. Gateway Employee Compensation uses ReportViewer (needs a real browser). Beacon GIS is JavaScript-heavy.

### Enable

In `~/.grok/config.toml`:

```toml
[mcp_servers.playwright]
enabled = true
command = "npx"
args = ["-y", "@playwright/mcp@latest", "--headless"]
startup_timeout_sec = 90
```

Browsers already installed on server:

```bash
npx playwright install chromium   # done 2026-07-06
```

Verify:

```bash
grok mcp doctor playwright
```

### Use cases

| Site | Tool |
|------|------|
| Gateway salary ReportViewer | Playwright export → `data/cache/salaries/` |
| beacon.schneidercorp.com | Parcel search samples per county |
| Any ASP.NET form Gateway page | Playwright click/fill |

Firecrawl is **not** a substitute for these.

---

## 6. Optional connectors

### Brave Search

```toml
[mcp_servers.brave-search]
enabled = true
# BRAVE_API_KEY in env — https://brave.com/search/api/
```

### Canva (already working via Grok OAuth)

Use for: county map Shorts thumbnails, "Top 5 anomalies" countdown graphics.

### reclaw-platform-remote (Tailscale)

```toml
[mcp_servers.reclaw-platform-remote]
enabled = true
url = "https://openclaw.tail20a090.ts.net/reclaw-mcp/mcp"
```

---

## 7. Config file locations

| File | Scope |
|------|-------|
| `/root/.grok/config.toml` | Global Grok/Composer on this server |
| `/root/ReClaw-2.0/.grok/config.toml` | Project overrides |
| `/root/ReClaw-2.0/.env` | API keys (never commit) |

After editing config, restart the agent session or run `grok mcp doctor`.

---

## 8. Quick reference — which tool for which audit job

| Job | Tool |
|-----|------|
| Disbursement math, Benford, vendors | `local_auditor_live` / Gateway cache |
| Budget YoY, ECOD, composition | `dogegpt_budget` + `pipeline_budget_anomalies.py` |
| Split-purchase pattern | `split_purchase_detector.py` |
| Peer outlier vs 92 counties | `county_peer_audit.py` |
| Find county PDFs / minutes | `firecrawl_discovery.py` |
| Export Gateway salaries | Playwright MCP (when enabled) |
| Write audit package to vault | `reclaw-platform__run_pike_winslow` |
| Human review before publish | County queue API `/county-queue/` |

---

## 9. Composer vs Grok Build

Both run on this Hetzner box with the same repo. **Composer** (Cursor) is fine for building and deploying. **Grok Build** adds native skill triggers (`reclaw-build`) and tighter MCP UI integration.

Neither replaces the other — same server, same code, same MCP config in `~/.grok/config.toml`.
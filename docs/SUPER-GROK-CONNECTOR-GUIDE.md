# SuperGrok × ReClaw Connector Guide

**Your paid SuperGrok chat, connected to your real fortress.**

**Last Updated:** 2026-07-10  
**Audience:** You (operator) — plain language, practical  
**Live connector:** ReClaw Platform MCP (`reclaw-platform`)  
**How to open this note in SuperGrok:**  
`Call read_vault_file with relative_path "Ravenstack/super-grok-connector-guide.md"`

---

## The point (read this once)

You pay for SuperGrok every month. You also run ReClaw on a Hetzner server (Docker, OpenClaw, county queue, Obsidian, pipelines).  

**Without the connector**, SuperGrok is smart but blind — it can’t see your stack, so you bounce to the server, run terminals, paste, repeat.  

**With the connector**, SuperGrok gets **eyes and hands** on that server. You ask in chat. Tools return **live** truth. SuperGrok turns that into advice, priorities, and fix plans.

| Role | Who |
|------|-----|
| **Brain** | SuperGrok (the chat app) |
| **Eyes / hands** | This MCP connector → your Hetzner box |
| **Workshop** | Grok Build on the server (deep code/deploy work) |

You still use Build when you need heavy engineering. Day-to-day status, pipeline questions, vault reads, and “what should I do?” live in SuperGrok.

---

## What this connector is

A standard **MCP (Model Context Protocol)** server named **reclaw-platform**, running on your server:

- Process: `scripts/reclaw_platform_mcp_server.py`
- Local port: **8100**
- Public HTTPS (SuperGrok): Cloudflare tunnel → must end with **`/mcp`**
- Tailnet: `https://openclaw.tail20a090.ts.net:8100/mcp`

**URL source of truth on the server:**  
`/root/ReClaw-2.0/data/mcp_public_url.txt`  

> Cloudflare quick tunnels can **rotate hostnames** when the tunnel restarts. If tools suddenly fail, re-copy that file into SuperGrok’s Custom Connector settings.

**Security (important):**  
The public HTTP MCP endpoint has **no login today**. Treat the public URL like a secret. Prefer Tailscale when you’re on a tailnet device. Don’t post the URL in public GitHub issues.

---

## The loop you want every day

```text
You (phone / SuperGrok)
  → SuperGrok
  → connector tools (live ReClaw)
  → SuperGrok explains / prioritizes / plans fixes
  → you approve anything risky
```

Not:

```text
You → SSH / Build → terminal soup → paste → SuperGrok → forget → repeat
```

---

## Killer combos (start here)

Copy-paste these into SuperGrok with the connector enabled.

### Morning brief

```text
Call project_sitrep. Then tell me: overall status, money/pipeline blockers, and the top 3 actions for me today. Be specific to THIS stack only.
```

### Full status only

```text
Call project_sitrep
```

(or simply: `Call sitrep`)

### Stuck county queue

```text
Call pipeline_status. Explain the pending review and what human approval means. Do not approve anything.
```

### What did the last run produce?

```text
Call inspect_session. Then read vault file Rural Data/_latest.md and summarize the package for me in plain English.
```

### “Is it on fire?”

```text
Call project_sitrep and docker_status. If something looks down, explain root cause and the safest fix order. Don't run destructive changes.
```

### Strategy from live data

```text
Call project_sitrep, pipeline_status, and query_knowledge for "faceless youtube rural data".
Using ONLY live tool results, what's the smartest next move this week?
```

### Architecture / rules check

```text
Call read_oracle. Am I using the MCP connector correctly for SuperGrok day-to-day ops?
```

### Open this guide again later

```text
Call read_vault_file with relative_path "Ravenstack/super-grok-connector-guide.md"
```

---

## Complete tool catalog

All tools below are on the **reclaw-platform** connector (names may appear with a prefix like `project_sitrep` depending on the client).

### Status & health (read-only — use freely)

| Tool | What it does | When to use |
|------|----------------|-------------|
| **`project_sitrep`** | **Star tool.** Full live fortress report in **plain English**: Docker, API, OpenClaw, Tailscale, MCP, Ollama, dashboard, county queue, sessions, packages, git (repo + vault), GitHub, Obsidian, RAG, gaps, next actions. | Morning check, “what’s going on?”, before asking for advice |
| **`sitrep`** | Exact alias of `project_sitrep` | Same as above; shorter name |
| **`stack_health`** | Runs the post-deploy healthcheck script (rawer than sitrep) | When sitrep looks odd and you want the full script output |
| **`docker_status`** | `docker compose ps` for the ReClaw stack | Container up/down only |
| **`reclaw_health`** | ReClaw API `/health` JSON | API-only ping |
| **`openclaw_health`** | OpenClaw gateway health | Gateway-only ping |
| **`git_status`** | ReClaw repo branch + dirty files | “Do I have uncommitted work?” |
| **`connector_help`** | How to attach clients (SuperGrok, Tailscale, SSH) | Setup / reconnect help |

### Pipeline & content factory (mostly read; one run tool)

| Tool | What it does | When to use |
|------|----------------|-------------|
| **`pipeline_status`** | Distilled snapshot: API, **county queue**, recent packages, recent sessions | Queue stuck? What’s pending approval? |
| **`inspect_session`** | Distilled audit of one session (handoff names, task, approval counts). Empty id = **latest**. Never dumps huge handoff JSON. | “What did the last pipeline run do?” |
| **`list_pipeline_sessions`** | Lists recent session folder names | Pick a session id for inspect |
| **`run_pike_winslow`** | **Runs** the rural_data pipeline (Researcher → Analyst → Obsidian). Defaults Pike/Winslow. | Only when you **intentionally** want a new package |

### Knowledge & Obsidian (your memory)

| Tool | What it does | When to use |
|------|----------------|-------------|
| **`query_knowledge`** | Semantic RAG search over vault + Ravenstack (citations) | “What do we know about X?” |
| **`read_oracle`** | Reads RAVENSTACK-ORACLE (optional section heading) | System rules, where to save/look |
| **`list_knowledge_topics`** | Lists Ravenstack markdown files | Browse the knowledge base |
| **`read_vault_file`** | Reads any file under the Obsidian vault (path relative to vault root) | Packages, this guide, review cards |
| **`read_repo_file`** | Reads any file under `/root/ReClaw-2.0` | Code, docs, scripts |

### Write & change (only when you mean it)

| Tool | What it does | Caution |
|------|----------------|---------|
| **`save_ravenstack_note`** | Writes a distilled note into Ravenstack backlog with frontmatter | Vault write |
| **`ingest_to_ravenstack`** | Distills + ingests content/path into backlog (ORACLE rules) | Vault write |
| **`write_vault_file`** | Creates/updates a vault file at a relative path | Powerful — be precise |
| **`rag_sync_vault`** | Re-indexes full vault into RAG | Can take a long time |

**Rule of thumb:** Reads = free. Writes and `run_pike_winslow` = say so clearly. County queue **approve/reject** stays a human gate (API/Build), not something SuperGrok should auto-do.

---

## How SuperGrok should behave (so you don’t get “paste into Build”)

Good SuperGrok behavior:

1. **Call the tool** in this chat.  
2. Use the **tool result** (especially `project_sitrep` plain English).  
3. Advise from **that** data.  
4. **Not** “paste this into Grok Build / SSH.”

If it starts hand-waving without tools, say:

```text
Actually call the connector tool. Don't guess. Don't send me to Grok Build.
```

---

## Adding more connectors (GitHub and friends)

The ReClaw connector is **one** MCP server. SuperGrok (and Grok Build) can attach **many** MCP connectors at once. Each one is a different “power pack.”

### Mental model

```text
SuperGrok chat
  ├── ReClaw Platform MCP  → your Hetzner fortress (this guide)
  ├── GitHub MCP           → issues, PRs, code on GitHub.com
  ├── Firecrawl (optional) → web scrape/search for audits
  └── …others as you add them
```

They don’t replace each other. They **stack**.

### What GitHub would give you

If GitHub MCP is connected and authenticated:

| Power | Example ask in SuperGrok |
|-------|---------------------------|
| List issues / PRs | “List open issues on jasandroidx/ReClaw-2.0” |
| Read issue detail | “Summarize issue #42 and propose a fix plan using project_sitrep context” |
| Recent commits | “What changed on the repo this week?” |
| Cross-link ops + code | “Sitrep says dirty tree — list uncommitted themes vs open PRs” |

**Combined killer combo:**

```text
Call project_sitrep.
Then (if GitHub connector is on) list open issues on jasandroidx/ReClaw-2.0.
Map each critical gap from sitrep to an issue or a new issue title I should file.
```

### How to add GitHub (high level)

**A) SuperGrok / grok.com Custom Connectors**

1. Open [grok.com/connectors](https://grok.com/connectors) (or app connector settings).  
2. Add a **Custom** connector when xAI / the client offers a GitHub or generic MCP option.  
3. Prefer **official GitHub MCP** or xAI marketplace GitHub if listed — auth is OAuth or a token.  
4. Enable it **alongside** ReClaw Platform (don’t remove ReClaw).  
5. New chat → try: “List my open issues on jasandroidx/ReClaw-2.0.”

Exact UI labels change; the idea is: **second connector, same chat.**

**B) Grok Build on the server** (workshop)

On Hetzner, Build can run GitHub MCP via `gh` auth if configured in `~/.grok/config.toml` / project config. Typical pattern:

1. `gh auth login` on the server (or token in env — never commit tokens).  
2. Add an `[mcp_servers.github]` block pointing at the official GitHub MCP server (or enable marketplace plugin).  
3. Restart the Grok Build session.  
4. Tools appear as `github__*`.

**C) Don’t put secrets in git**

- Tokens → env / OpenClaw secrets / connector OAuth  
- Never paste PATs into vault notes or public chats  

### Other connectors worth knowing

| Connector | Powers you’d gain | Notes |
|-----------|-------------------|--------|
| **Firecrawl** | Web search/scrape for county sites, SBOA PDFs | Already useful for rural_data Tier-3; needs API key |
| **Obsidian** (if separate) | Vault-focused tools | You already cover vault via ReClaw `read_vault_file` / write |
| **Gmail / Calendar** (if offered) | Inbox / schedule | Usually OAuth; separate from ReClaw |
| **Gemini / other MCP clients** | Same ReClaw URL if they support remote MCP | Protocol-universal; app UI varies |
| **Perplexity** | Web research | Usually **not** custom MCP host — use for open web, not fortress control |

### “Universal” in plain English

- **Protocol:** Yes — anything that speaks **MCP over HTTP** can use your ReClaw URL.  
- **Every consumer app:** No — SuperGrok yes; many Gemini setups yes; Perplexity usually no.  
- **Best daily driver for you:** SuperGrok + ReClaw connector (+ GitHub when you add it).

---

## SuperGrok vs Grok Build (when to use which)

| Task | Where |
|------|--------|
| Status, queue, advice, vault reads, “what next?” | **SuperGrok + connector** |
| Multi-file refactors, deploy surgery, systemd, long debugging | **Grok Build on server** |
| Open web research | SuperGrok or Perplexity |
| Filing issues / PR review once GitHub is connected | SuperGrok with GitHub MCP, or Build |

Using SuperGrok for daily ops **saves Build tokens** for real engineering. That’s the responsible split you described.

---

## Quick reference: endpoints

| Plane | Endpoint |
|-------|----------|
| Public (SuperGrok) | Contents of `data/mcp_public_url.txt` (must end `/mcp`) |
| Tailscale IP | `https://openclaw.tail20a090.ts.net:8100/mcp` · health `…/health` |
| Health check | `GET …/health` → `{"status":"ok","service":"reclaw-platform",…}` |

Server ops (if something dies — you or Build):

```bash
systemctl status reclaw-mcp-bridge reclaw-mcp-tunnel
cat /root/ReClaw-2.0/data/mcp_public_url.txt
curl -sS http://127.0.0.1:8100/health
```

---


### Operator expansions (2026-07-10)

| Tool | Purpose |
|------|---------|
| `morning_digest` | Phase B morning brief (sitrep + queue + suggested actions; optional vault write) |
| `county_queue_card` | Read-only Gibson-style review card |
| `pending_gates` | All human gates at a glance |
| `connector_status` / `public_mcp_url` | Tunnel URL + health (after rotate) |
| `openclaw_models` / `ollama_models` | Cost routing inventory |
| `git_vault_status` | Repo + vault dirty |
| `list_packages` / `package_summary` | Content packages |
| `github_gap_suggestions` | Issue titles from gaps (does not file) |
| `skill_stack_map` | Firecrawl / Chrome / CF / Superpowers map |
| **GATED** `county_queue_approve` / `reject` / `run_next` | `confirm=true` only when you explicitly ask |
| **GATED** `re_export_package` / `session_approve_capability` | Same gate rule |

**40 tools** on reclaw-platform. Prefer reads. Never auto-approve from Automations.


## Security cheat sheet

1. Public tunnel URL ≈ secret.  
2. Prefer Tailscale when possible.  
3. Reads free; writes/pipeline only with clear intent.  
4. County approve/reject = human gate.  
5. No API keys in vault notes.  
6. After tunnel restart, refresh SuperGrok connector URL.

---

## One-page “what do I say?”

| Goal | Say this |
|------|----------|
| Everything status | `Call project_sitrep` |
| Queue only | `Call pipeline_status` |
| Last run | `Call inspect_session` |
| Search memory | `Call query_knowledge for "…"` |
| Read this guide | `Call read_vault_file with relative_path "Ravenstack/super-grok-connector-guide.md"` |
| Advice | Sitrep first, then: “Top 3 actions for revenue this week from live data only.” |
| Don’t guess | “Call the tool. Don’t send me to Build.” |

---

## Related paths

| Path | Role |
|------|------|
| Vault: `Ravenstack/super-grok-connector-guide.md` | **This document** (chat-readable) |
| Vault: `Ravenstack/mcp-connector.md` | Technical map / security |
| Vault: `RAVENSTACK-ORACLE.md` | System SOT |
| Repo: `docs/SUPER-GROK-CONNECTOR-GUIDE.md` | Mirror of this guide |
| Repo: `docs/MCP_CONNECTOR.md` | Operator tech notes |
| Skill (Build only): `ravenstack-sitrep` | Full sitrep skill on server |

---

## Closing

You didn’t build a toy. You built a **remote operator console** for a real multi-service money-making stack, wired into the chat subscription you already pay for.

- **SuperGrok** = daily command and advice  
- **Connector** = live ReClaw truth  
- **Build** = deep workshop  

Start every serious day with **`project_sitrep`**. Stay in the same chat for advice. Add **GitHub** when you want issues/PRs in that same conversation. Come back to this note anytime with `read_vault_file`.

*Welcome to the fortress — from your phone.*

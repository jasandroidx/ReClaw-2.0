# ReClaw 2.0

**Clean Rebuild of OpenClaw for Rural Data Faceless Channel Swarm + Local Monetization**

A practical, production-ready OpenClaw setup for building and running an agent swarm that researches public data, analyzes red flags in local economies/budgets/salaries, and generates complete content packages for a faceless YouTube/TikTok/Shorts channel. It also supports real-world side hustles and services in rural Indiana.

**Repo Purpose**: Clean foundation after previous OpenClaw instances became bloated and confusing between local PC and Hetzner. Fresh, maintainable start with clear architecture, strong security, Docker deployment, Tailscale access, and direct integration with your tools (Obsidian, Notion, Discord).

Drawn from best practices in:
- Official OpenClaw architecture & security patterns
- *Make Money with OpenClaw in 30 Days* (Patrick Andrei)
- *Automate Everything: The OpenClaw Handbook* (Kelly Claude)
- *OpenClaw: The Complete Guide* (Orange Paper)

## Core Goals
- Hetzner as single production instance (with GPU)
- Local PC as clean dev mirror (git-based)
- Agent swarm that outputs directly to Obsidian
- Controllable via Discord bot (primary) + optional Web UI
- Docker for consistency and easy updates
- Tailscale for simple remote access (no more manual SSH tunnel hassle)
- Strong security by default
- Ready for the Rural Data Faceless Channel + real local monetization

## Architecture (Inspired by Official OpenClaw Patterns)

### Core Structure
- **Gateway**: Root control plane (WebSocket orchestration, model routing)
- **Agents**: Logic layer with session isolation and memory
- **Channels**: Discord (primary), with room for WhatsApp/Telegram later
- **Tools/Skills**: Modular execution layer (browser, file system, data pulling, with approval gates)

### Agent Identities & Routing
Each agent has a clear identity (SOUL.md style) and explicit permissions/routing rules (AGENTS.md style). No agent gets blanket access to shell or browser actions.

### Starting Swarm
1. **Researcher Agent** — Pulls public data (county sites, budgets, salary records, property data). Outputs structured JSON + summary.
2. **Analyst / Red Flag Agent** — Interprets data into practical rural insights, budget implications, and job market red flags.
3. **Orchestrator** — Coordinates the above and assembles the final content package (script outline, visual prompts, thumbnail ideas, affiliate suggestions).

Later expansion: Scriptwriter + Visuals agents (using your local ComfyUI/SD or Grok Imagine).

### Handoff Format
Clean structured JSON between agents. Example in `docs/handoff-example.json`.

### Memory & Context
- Short-term: JSON handoff only
- Long-term: Obsidian notes + project context files

## Security (Non-Negotiable)
- Least privilege by default
- Manual approval gates for any shell, browser, or network actions
- Docker sandboxing for higher-risk execution
- Non-root service accounts where possible
- Session isolation between agents
- API keys scoped appropriately

## Deployment (Docker + Tailscale)

### Docker
`docker-compose.yml` for Hetzner production with GPU support. The same setup works on your local dev mirror with smaller models.

### Tailscale
Recommended for simple, secure access from phone, laptop, or truck. One-command connection. Full guide in `docs/tailscale.md`. Clean SSH key fallback also documented.

## Integration with Your Stack
- **Obsidian**: Agents write research, scripts, and final packages as markdown
- **Notion**: High-level command center (this repo is linked from the page we created)
- **Discord Bot**: Primary control interface (revive and expand your previous working bot)
- **Web UI** (optional): Gradio or Streamlit dashboard for visual review of outputs

## Monetization Angle
This directly powers your Rural Data Faceless Channel. It can also serve as the foundation for:
- Freelancing AI automation/research services
- Local AI services for rural Indiana businesses (GBP cleanup, review management, content)
- Building an automation agency or selling digital products (templates, toolkits, prompt packs)

## Getting Started
1. Clone the repo
2. Follow `docs/setup.md` for Docker on Hetzner + Tailscale + security basics
3. Test the swarm on sample data (Pike County example included)
4. Connect your Discord bot
5. Start generating content packages

## Repo Structure
- `README.md` (this file)
- `docs/` — Architecture, handoffs, setup guides, Tailscale, security, monetization notes
- `agents/` — Individual agent code (with identity files)
- `docker/` — docker-compose.yml and related files
- `api/` — FastAPI control layer
- `examples/` — Sample outputs and test data

## Next Steps in This Repo
- Full agent implementations (Researcher + Analyst first, with proper identities and security gates)
- Docker Compose with GPU support
- Discord bot integration example
- Sample content package that writes cleanly to Obsidian
- Integration with local business prospecting workflows

This is the clean, secure, and directly useful foundation we've been building toward. No more bloat or machine confusion.

Let's make it profitable.

---
*ReClaw 2.0 — Clean OpenClaw that actually helps you make money in rural Indiana.*

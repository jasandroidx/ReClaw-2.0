# ReClaw 2.0

**Clean Rebuild of OpenClaw for Rural Data Faceless Channel Swarm**

A practical, production-ready OpenClaw setup tailored for building and running an agent swarm that researches public data, analyzes red flags in local economies/budgets/salaries, and generates complete content packages for a faceless YouTube/TikTok/Shorts channel.

**Repo Purpose**: Clean foundation after previous OpenClaw instances became bloated and confusing between local PC and Hetzner. Fresh, maintainable start with clear architecture, Docker deployment, Tailscale access, and direct integration with your tools (Obsidian, Notion, Discord).

Drawn from best practices in the PDFs you shared:
- *Make Money with OpenClaw in 30 Days* (Patrick Andrei) — business models and monetization paths
- *Automate Everything: The OpenClaw Handbook* (Kelly Claude) — automation patterns, memory systems, multi-agent orchestration
- *OpenClaw: The Complete Guide* (Orange Paper) — architecture, deployment, Docker

## Core Goals
- Hetzner as single production instance
- Local PC as clean dev mirror (git-based)
- Agent swarm that outputs directly to Obsidian
- Controllable via Discord bot (primary) + optional Web UI
- Docker for consistency
- Tailscale for simple remote access (no more manual SSH tunnel hassle)
- Ready for the Rural Data Faceless Channel + future monetization (freelancing, automation services, digital products)

## Architecture

### Principles
- Single-responsibility agents with structured JSON handoffs
- Minimal state
- Everything through clean API on Hetzner
- Outputs default to markdown files in your Obsidian vault
- Clear production (Hetzner) vs dev (local) separation

### Starting Swarm
1. **Researcher Agent** — Pulls public data (county sites, budgets, salary records, property data). Structured JSON + summary.
2. **Analyst / Red Flag Agent** — Interprets data into practical rural insights, budget implications, job market red flags.
3. **Orchestrator** — Coordinates, assembles final content package (script outline, visual prompts, thumbnail ideas, affiliate suggestions).

Later expansion: Scriptwriter + Visuals agents (leveraging your local ComfyUI/SD or Grok Imagine).

### Handoff Format
Clean JSON between agents. Example in `docs/handoff-example.json`.

### Memory & Context
- Short-term: JSON handoff only
- Long-term: Obsidian notes + project context files (inspired by handbook patterns)

### API Layer
FastAPI on Hetzner. Discord bot and Web UI talk to this.

## Deployment (Docker + Tailscale)

### Docker
`docker-compose.yml` for Hetzner production (with GPU support for image generation). Same setup works on local dev mirror with smaller models.

### Tailscale
Recommended for simple, secure access from phone/laptop/truck. One-command connection. Full guide in `docs/tailscale.md`. SSH key fallback also documented.

## Integration with Your Stack
- **Obsidian**: Agents write research, scripts, and packages to your preferred folder
- **Notion**: High-level command center (this repo is linked from the page we created)
- **Discord Bot**: Primary control interface (revive and expand your previous working bot)
- **Web UI** (optional): Gradio or Streamlit dashboard for visual review of outputs

## Monetization Angle
This powers your Rural Data Faceless Channel directly. It can also become the base for freelancing similar AI automation/research services, building an automation agency, or selling digital products (templates, toolkits, prompt packs) — ideas drawn from the PDFs.

## Getting Started
1. Clone the repo
2. Follow `docs/setup.md` for Docker on Hetzner + Tailscale
3. Test the swarm on sample data (Pike County example included)
4. Connect your Discord bot
5. Start generating content packages

## Repo Structure
- `README.md` (this file)
- `docs/` — Architecture, handoffs, setup guides, Tailscale, monetization notes
- `agents/` — Individual agent code
- `docker/` — docker-compose.yml and related
- `api/` — FastAPI layer
- `examples/` — Sample outputs and test data

## Next Steps in This Repo
- Full agent implementations (Researcher + Analyst first)
- Docker Compose with GPU support
- Discord bot integration example
- Sample content package that writes to Obsidian
- More from the PDFs (business models, advanced patterns)

This is the clean, permanent foundation we've been building toward. No more bloat or machine confusion.

Let's make it profitable.

---
*ReClaw 2.0 — Clean OpenClaw for the Rural Data Faceless Channel and whatever comes next.*

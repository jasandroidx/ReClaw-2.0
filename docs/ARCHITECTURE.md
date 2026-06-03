# ARCHITECTURE.md — ReClaw 2.0 (OpenClaw-aligned)

## High Level

Gateway (control plane)
  └── creates Session (isolation)
        ├── loads SOUL.md (system + per-agent)
        ├── creates SecurityManager (permissions + gates)
        └── invokes Orchestrator
              ├── Researcher (with gate checks)
              ├── Analyst
              └── quality gates → ContentPackage
                    └── ObsidianWriter (channel)

All durable communication = JSON files in the session handoffs/ dir.

## Why This Shape

- Matches the patterns in the parent ~/clawd workspace (SOUL, AGENTS, handoff protocol, file-as-memory).
- Matches the official OpenClaw Gateway + agents + Tailscale + session concepts visible in the Obsidian knowledge base and plugin.
- Gives us security (gates), audit (sessions), and human review surface (Obsidian) with almost zero moving parts.

## Components

- `core/handoff.py` — the schema contract (never change lightly)
- `core/session.py` — the isolation mechanism
- `core/security.py` — capability declarations + gate enforcement
- `agents/*/SOUL.md` — identity loaded fresh every run
- `AGENTS.md` + `SOUL.md` (root) — routing + non-negotiables
- `api/main.py` — the Gateway HTTP surface (can later become a standalone `gateway/` package)
- `channels/` (future) — other writers (Discord, etc.)

## Docker View

One main container for the Gateway + in-process agents (simple and sufficient for the data volume we expect).

Later, when we have heavy LLM agents or many concurrent business jobs, we can split into:
- gateway container (orchestration only)
- worker containers per agent type, given only their session dir as a volume mount

GPU is available on the host for future local models (Ollama/vLLM service in compose).

## Data Flow for a Typical Run

1. POST /trigger/Pike → Gateway
2. Gateway: create_session(), pre-grant low-risk caps, possibly grant live_fetch if auto_approve
3. Orchestrator(session) → Researcher(session) → does seed or gated live → writes researcher.json
4. Orchestrator → Analyst(session) → writes analyst.json
5. Orchestrator enforces gates, assembles, writes run artifact + calls ObsidianWriter
6. ObsidianWriter drops the .md + .json sidecar in the vault path
7. Status returned / pollable

Every step is logged in the session. You can point at an old session and replay just the analyst step if you improve the heuristics.

This is production-minded minimalism.

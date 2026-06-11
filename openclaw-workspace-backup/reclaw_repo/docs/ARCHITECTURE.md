# ARCHITECTURE.md — ReClaw 2.0 (OpenClaw-aligned Platform)

## High Level (Domain-Agnostic Core)

Core Platform (domain agnostic):
- Gateway (control plane, api/main.py)
  └── creates Session (isolation, core/session.py)
        ├── loads SOUL.md (system + per-domain-agent)
        ├── creates SecurityManager (core/security.py, permissions + gates)
        ├── manages events (future JSON contract for visual office)
        └── invokes Orchestrator (per-domain)
              ├── Domain agents (e.g. rural_data/researcher with gate checks)
              ├── Analyst / other specialists
              └── quality gates → ContentPackage
                    └── ObsidianWriter (core/obsidian_writer.py or domain channel)

All durable communication = JSON files in the session handoffs/ dir + explicit event/state records.

## Why This Shape

- Matches the patterns in the parent ~/clawd workspace (SOUL, AGENTS, handoff protocol, file-as-memory, approval gates).
- Matches official OpenClaw Gateway + agents + Tailscale + session + Obsidian concepts.
- Core is general-purpose platform; rural_data is first module. Gives security (gates), audit (sessions), durable memory (Obsidian), and first-class event model for future visual frontend with almost zero moving parts. Domain isolation allows clean addition of grants, local_leads, content, visual_office etc.

## Components

**Core Platform (domain-agnostic):**
- `core/handoff.py` + future events.py — schema + JSON event/state contract (`agent_id`, `role`, `state`, `current_task`, `started_at`, `updated_at`, `last_result`, `last_error`, `run_id`)
- `core/session.py` — isolation mechanism (sessions/ as truth)
- `core/security.py` — capability declarations + gate enforcement (shared)
- `core/config.py`, `core/obsidian_writer.py` — shared infrastructure
- `AGENTS.md` + root `SOUL.md` — platform routing + non-negotiables

**Domain modules (e.g. rural_data):**
- `agents/researcher.py` + `agents/researcher/SOUL.md`, `agents/analyst.py` etc.
- `api/main.py` — the Gateway HTTP surface (domain routing via AGENTS.md; can later become standalone `gateway/` package)

`channels/` and per-domain orchestrators (future).

## Docker View

One main container for the Gateway + in-process agents (simple and sufficient for MVP data volume). /root/obsidian_vault:/vault is current Phase 1 choice.

Later: split into gateway + per-domain workers (only their session dir mounted). GPU for future LLMs. Visual frontend consumes event JSON (out of scope).

This supports multiple domains cleanly while preserving OpenClaw conventions.

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

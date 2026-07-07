# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`AGENTS.md`** at the repo root — platform routing, agent roster, county-queue workflow.
- **`data/reclaw_orchestration.yaml`** — deployed vs backlog detectors and media pipeline.
- **Obsidian vault (source of truth)** — `/root/obsidian_vault/Ravenstack/RAVENSTACK-ORACLE.md` and `RAVENSTACK-ARCHITECTURE.md` for platform rules and provenance constraints.
- **`docs/adr/`** — when present, read ADRs that touch the area you're about to work in.

`CONTEXT.md` is not yet maintained at the repo root; domain terms for Indiana county audit live in the vault and `data/fraud_scheme_taxonomy.yaml`. Proceed without flagging absence — use `/domain-modeling` when glossary gaps block work.

## File structure

Single-context repo:

```
/
├── AGENTS.md
├── data/reclaw_orchestration.yaml
├── docs/agents/          ← Matt Pocock skills config (this folder)
├── docs/adr/             ← create when architectural decisions are recorded
└── tools/                ← detectors, scriptwriter, remotion orchestrator
```

## ReClaw-specific vocabulary

When naming domain concepts in issues or refactors, prefer existing repo terms:

- **County queue** — 92-county human-gated audit cursor (`core/county_queue.py`)
- **Red flag** — provenance-backed anomaly (`core/handoff.py` `RedFlag`)
- **Gateway** — Indiana flat-file truth (`tools/indiana_gateway.py`), not OpenClaw gateway unless context says otherwise
- **Fair-report** — patterns in public records; never crime allegations in hooks

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding.
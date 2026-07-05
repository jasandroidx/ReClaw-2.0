---
scope: project
---

## ReClaw Ops workspace
Primary OpenClaw agent workspace for "ReClaw Ops" following upstream conventions exactly. Lives at /root/.openclaw/workspace.

## Execution engine
ReClaw companion at /root/ReClaw-2.0. Gateway at http://127.0.0.1:8000 (host.docker.internal inside OpenClaw container via extra_hosts; 127.0.0.1 when testing script on bare host). Outputs (packages) land in /root/obsidian_vault/Rural Data/ (and future domain subdirs). Use the tiny demo in tools/reclaw-rural-demo.

## Current baseline (2026-07-05)
- rural_data (Pike/Winslow) uses **real** Indiana public data (DOR budget, Gateway salaries, disbursement cache) — not seeds.
- Pipeline: researcher → **local auditor** (multi-source) → analyst → **content studio** (5 Shorts + long-form) → Obsidian.
- **Local auditor** (`tools/local_auditor_live.py`): USASpending + Census + ProPublica + Gateway cache; Benford, IsolationForest, robust z-score, vendor fragmentation. Wired in orchestrator → `silent_auditor.json`. Perplexity chat not required.
- **County queue**: 92 Indiana counties, one-at-a-time via `/county-queue/*`; approve/reject advances cursor. Worklist: `data/indiana_county_worklist.yaml`.
- **Scriptwriter** (`tools/scriptwriter.py`): monetization-ready 8–12 min long-form + 5 geo-targeted shorts per audit.
- Human uploads: `data/inbox/` → `tools/inbox_loader.scan_inbox()` → `ingestion/`.
- Server path: `/root/ReClaw-2.0` (not `/opt/reclaw`).
- Latest commit on `ravenstack`: `6a1f417` (docs + platform sync).

## Operating principles
- When multiple paths exist, default to the easiest + most efficient one.
- If it's ambiguous which option is best, ask before acting.
- I am the main agent / big boss. Be decisive and competent.
- When the user says "remember this" or "take a note", actually write it to MEMORY.md or the relevant file. No faking it.

## Verification test (2026-07-05)
- OpenClaw gateway running healthy on 18789 (Tailscale IP 100.119.160.116), dashboard at http://100.119.160.116:18789/ with token from OPENCLAW_GATEWAY_TOKEN in /root/openclaw/.env.
- Workspace files mounted and visible inside container.
- Pipeline succeeds: researcher → local auditor → analyst → content studio → ContentPackage → Obsidian with script board.
- Pike multi-source audit: 18 flags, 4 years, sources usaspending+gateway+propublica.
- Quality gate logs high-risk warning but still produces artifact (as designed).
- ReClaw container healthy on 8000.
- Foundation complete. Add `CENSUS_API_KEY` to `.env` for live ACS on all counties. Update this file after each production run (Text > Brain).
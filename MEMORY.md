---
scope: project
---

## ReClaw Ops workspace
Primary OpenClaw agent workspace for "ReClaw Ops" following upstream conventions exactly. Lives at /root/.openclaw/workspace.

## Execution engine
ReClaw companion at /root/ReClaw-2.0. Gateway at http://127.0.0.1:8000 (host.docker.internal inside OpenClaw container via extra_hosts; 127.0.0.1 when testing script on bare host). Outputs (packages) land in /root/obsidian_vault/Rural Data/ (and future domain subdirs). Use the tiny demo in tools/reclaw-rural-demo.

## Current baseline (2026-07-05)
- rural_data (Pike/Winslow) uses **real** Indiana public data (DOR budget, Gateway salaries, disbursement cache) — not seeds.
- Pipeline: researcher → analyst (36 red flags, risk 10.0) → **content studio** (3 Shorts scripts) → Obsidian.
- Vault `Rural Data/2026-07-05-pike-winslow.md` includes Short-Form Scripts section with `pending_approval`.
- Human uploads: `data/inbox/` → `tools/inbox_loader.scan_inbox()` → `ingestion/`.
- Local auditor: `tools/local_auditor_live.py` (Benford, dominant line, vendor concentration) wired in orchestrator → `silent_auditor.json`. Perplexity chat not required.
- Server path: `/root/ReClaw-2.0` (not `/opt/reclaw`).

## Operating principles
- When multiple paths exist, default to the easiest + most efficient one.
- If it's ambiguous which option is best, ask before acting.
- I am the main agent / big boss. Be decisive and competent.
- When the user says "remember this" or "take a note", actually write it to MEMORY.md or the relevant file. No faking it.

## Verification test (2026-07-05)
- OpenClaw gateway running healthy on 18789 (Tailscale IP 100.119.160.116), dashboard at http://100.119.160.116:18789/ with token from OPENCLAW_GATEWAY_TOKEN in /root/openclaw/.env.
- Workspace files mounted and visible inside container.
- Pipeline succeeds: researcher → analyst (36 flags, risk 10.0) → content studio (3 Shorts) → ContentPackage → Obsidian with script board.
- Quality gate logs high-risk warning but still produces artifact (as designed).
- ReClaw container untouched, healthy on 8000.
- Foundation complete. Next real runs can use live_fetch (with approval) or new counties. Update this file after each production run (Text > Brain).

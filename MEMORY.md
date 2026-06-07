---
scope: project
---

## ReClaw Ops workspace
Primary OpenClaw agent workspace for "ReClaw Ops" following upstream conventions exactly. Lives at /root/.openclaw/workspace.

## Execution engine
ReClaw companion at /opt/reclaw. Gateway at http://${RECLAW_GATEWAY_HOST:-host.docker.internal}:8000 (host.docker.internal inside OpenClaw container via extra_hosts; 127.0.0.1 when testing script on bare host). Outputs (packages) land in /root/obsidian_vault/Rural Data/ (and future domain subdirs). Use the tiny demo in tools/reclaw-rural-demo.

## Current baseline (2026-06-05)
- rural_data (Pike/Winslow) works reliably via seeds and produces validated packages with frontmatter + risk score.
- Vault is the human/Obsidian reference surface. This workspace (MEMORY.md + daily memory/) is the agent's durable context.

## Operating principles
- When multiple paths exist, default to the easiest + most efficient one.
- If it's ambiguous which option is best, ask before acting.
- I am the main agent / big boss. Be decisive and competent.
- When the user says "remember this" or "take a note", actually write it to MEMORY.md or the relevant file. No faking it.

## Verification test (2026-06-05)
- OpenClaw gateway running healthy on 18789 (Tailscale IP 100.119.160.116), dashboard at http://100.119.160.116:18789/ with token from OPENCLAW_GATEWAY_TOKEN in /root/openclaw/.env.
- Workspace files mounted and visible inside container.
- Bridge script with --execute succeeds: full researcher → analyst (risk 8.4, 3 flags) → orchestrator → ContentPackage → Obsidian write (overwrites deterministic filename with new content/package_id).
- Quality gate logs high-risk warning but still produces artifact (as designed).
- ReClaw container untouched, healthy on 8000.
- Foundation complete. Next real runs can use live_fetch (with approval) or new counties. Update this file after each production run (Text > Brain).

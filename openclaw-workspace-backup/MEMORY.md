---
scope: project
---

## ReClaw Ops workspace
Primary OpenClaw agent workspace for "ReClaw Ops" following upstream conventions exactly. Lives at /root/.openclaw/workspace.

## Infrastructure: The "Host-Docker Bridge" (Updated 2026-06-11)
- The gap between Docker containers and the host machine is bridged via `host.docker.internal`.
- **Tailscale IP:** 100.119.160.116
- This allows agents to reach local services like Ollama (port 11434) and the Gateway (port 8000).
- **Key Ports:**
  - 8000: OpenClaw Gateway
  - 8001: ReClaw API (Moved from 8000 to avoid conflict)
  - 8080: Visual Dashboard
  - 11434: Ollama (LLM Brain)
- **Capability:** Local LLM usage means zero-cost tokens for autonomous loops; we can be more aggressive with research and analysis.
- **Memory:** Embeddings for the Vault/Memory now use this bridge, enabling semantic search (searching by meaning rather than just keywords).


## Current baseline (2026-06-05)
- rural_data (Pike/Winslow) works reliably via seeds and produces validated packages with frontmatter + risk score.
- Vault is the human/Obsidian reference surface.
- This workspace (MEMORY.md + daily memory/) is the agent's durable context.

## Operating principles
- When multiple paths exist, default to the easiest + most efficient one.
- If it's ambiguous which option is best, ask before acting.
- I am the main agent / big boss. Be decisive and competent.
- When the user says "remember this" or "take a note", actually write it to MEMORY.md or the relevant file.

## Current priorities

### Clawsmith (Ambitious version)
- Clawsmith is the powerful room architect.
- It lives in its own dedicated room on the visual dashboard.
- When given a new idea, it designs complete rooms (agents, roles, tools, memory, layout) and outputs files for human review before anything is built.
- This is the full ambitious version, not a lightweight conversational agent.

### RaterHub / SxS Rating Automation (Important - 2026-06-07)
User currently uses Perplexity Comet for Side-by-Side Search Quality Rating tasks on RaterHub (Telus International / Google).

Future direction: Transition this work to the agent. Browser automation will be required. Safety-first approach preferred (user stays logged in, agent assists via analysis/screenshots/guidance rather than direct login).

## Verification test (2026-06-05)
- OpenClaw gateway running healthy on 18789 (Tailscale IP 100.119.160.116).
- rural_data end-to-end works with seeds.
- Foundation complete. Next real runs can use live_fetch (with approval) or new counties.

---

## Archived Notes

### Discord Integration Ideas (2026-06-07)
Long brainstorm of Discord ideas saved for future reference. Not currently active.

**Core Approach (Recommended)**
- Use one Discord connection.
- Agents post with distinct personalities.
- Discord acts as the casual "break room" layer.

**Useful / Production Ideas**
- Approval workflows via reactions
- Session threads with handoff logs
- Live agent status / presence
- Review queue channel
- Polls, image drops, thread-per-county

**Fun / Cool Ideas**
- Agent Break Room banter
- Meme generation
- Personality clashes
- Lore building, Failure Theater, Roast channel, etc.

(Full original notes preserved in previous version of this file if needed.)
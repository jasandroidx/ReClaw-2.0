# ReClaw-2.0 / Ravenstack Fortress — Development Rules

## Single Source of Truth (SOT)
- The master knowledge base and long-term memory lives at: `/root/obsidian_vault/Ravenstack/`
- All persistent notes, memory, and structured data should be written as clean Markdown files with valid YAML frontmatter when appropriate.
- Avoid raw data dumps. Distill information into readable, well-structured notes.

## Safety Rules
- Never perform recursive or broad deletions outside of explicitly allowed paths.
- All file operations should stay within these two locations when possible:
  - `/root/ReClaw-2.0/`
  - `/root/obsidian_vault/Ravenstack/`
- Prefer using the custom FastMCP server (`reclaw-platform` on port 8100) for file operations on the vault instead of raw terminal commands when practical.

## Architecture Overview
- **Runtime**: OpenClaw running on Hetzner VPS (Docker + Tailscale)
- **Main Agent**: Currently simplifying toward one strong, reliable main agent
- **Memory Layer**: Ravenstack (Obsidian) + custom FastMCP server
- **Model Strategy**: Default to cheap/local models (Ollama on the server). Use powerful paid models only when higher quality or deeper reasoning is needed.

## Current Priorities
- Stabilize and simplify the main agent
- Reduce unnecessary complexity and risk of breaking the running system
- Make Ravenstack a reliable, queryable long-term memory system
- Keep the overall setup maintainable

## Always use available skills, plugins, MCP, and hooks

**Mandatory default — not optional.** On every non-trivial task, actively use the tools already available instead of guessing from memory or only using shell.

1. **MCP connectors first** (especially `reclaw-platform` / Ravenstack on :8100):
   - Status: `project_sitrep`, `sitrep`, `morning_digest`, `stack_health`, `docker_status`
   - Queue: `county_queue_card`, `pending_gates` (approve/reject only with explicit human OK)
   - Knowledge: `query_knowledge`, `read_oracle`, `read_vault_file`, `list_knowledge_topics`
   - Prefer MCP vault R/W over ad-hoc vault shell when practical
2. **Project / Grok skills** when they match the work:
   - Platform/ops: `reclaw-build`, `ravenstack-sitrep`, `county-audit`
   - Engineering: TDD, systematic-debugging, codebase-design, review, check-work, writing-plans
   - Docs/files: obsidian, firecrawl (search/scrape), github, etc.
3. **OpenClaw plugins & CLI** for gateway/agent/channel work:
   - `openclaw doctor --lint`, `plugins inspect/list`, `channels status --probe`, `agents list --bindings`, `devices list`, `qr`
   - After `openclaw.json` or plugin changes: doctor + health check; respect single-gateway rule (Docker `openclaw-gateway` only)
4. **Hooks / automation** already on the host (timers, guards, MCP bridge): use and verify them rather than inventing parallel mechanisms
5. **First-read for system context:** Ravenstack `wiki/hot.md` → ORACLE/architecture → live MCP/tools

**Anti-patterns (do not do these):**
- Claiming stack/queue/model status without probing (sitrep, `/state`, docker, openclaw health)
- Ignoring an installed skill/MCP that clearly fits the task
- Telling the user to “paste into Grok Build” or re-run work that MCP can do in-chat
- Spinning up a second OpenClaw gateway (ruins sessions/Discord/config)

If a skill or MCP is unavailable, say so briefly and fall back — do not silently skip verification.

## Working Style
- Be direct and practical.
- When making changes, briefly explain the reasoning and any risks.
- Validate configuration changes when relevant (e.g. run `openclaw doctor --lint` after editing `openclaw.json`, plus live health probes).
- If something looks risky or could affect the running gateway, flag it clearly before proceeding.
- Prefer making changes through structured files (`SOUL.md`, config files, markdown notes) rather than one-off terminal commands when possible.
- Prefer evidence from tools over prior chat assumptions.

## Communication
- Keep responses focused and actionable.
- When the user wants to move fast, match their pace.
- When something is unclear or risky, ask for clarification instead of guessing.

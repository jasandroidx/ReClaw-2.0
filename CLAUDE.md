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

## Working Style
- Be direct and practical.
- When making changes, briefly explain the reasoning and any risks.
- Validate configuration changes when relevant (e.g. run `openclaw doctor` after editing `openclaw.json`).
- If something looks risky or could affect the running gateway, flag it clearly before proceeding.
- Prefer making changes through structured files (`SOUL.md`, config files, markdown notes) rather than one-off terminal commands when possible.

## Communication
- Keep responses focused and actionable.
- When the user wants to move fast, match their pace.
- When something is unclear or risky, ask for clarification instead of guessing.

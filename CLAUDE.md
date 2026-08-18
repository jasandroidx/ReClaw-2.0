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




## Delivery rules (Jason)

- Say **"outbox"** / **"send me the document"** / **"put it where I can open it"** → permanent web outbox only. No email unless asked.
- Say **email** → then email.

## Permanent outbox (hard rule — agents keep forgetting this)

**URL:** http://100.108.130.82:8765/  
**Host path:** `/root/outbox`  
**Home page:** `/root/outbox/index.html` (curated — **not** an auto file list)

**Writing a file into `/root/outbox` alone is NOT delivery.** Jason opens `index.html`. Unlinked files look “missing.”

**Always:**

```bash
# after writing /root/outbox/YOUR-FILE.md
outbox-publish /root/outbox/YOUR-FILE.md --title "Human label"
```

Then reply with **both** home + direct URLs:

- http://100.108.130.82:8765/
- http://100.108.130.82:8765/YOUR-FILE.md

SOT: `data/PERMANENT-OUTBOX-MEMORY.md` · `/root/outbox/PERMANENT-OUTBOX-MEMORY.md` · vault `Ravenstack/ops/OUTBOX.md`

## Fortress (vocabulary — permanent)

**Fortress** means the entire system: OpenClaw + ReClaw + this repo + Ravenstack/Obsidian + Docker + Tailscale + MCP + paired nodes. A **fortress sitrep** audits all of it (`ravenstack-sitrep` / `project_sitrep`). **OpenClaw Mechanic** (skill `openclaw-mechanic` (legacy `reclaw-build`)) fixes/builds/advises under that whole umbrella and should sitrep first when status is unclear.

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
   - Platform/ops: `openclaw-mechanic` (legacy alias reclaw-build), `ravenstack-sitrep`, `county-audit`
   - Engineering: TDD, systematic-debugging, codebase-design, review, check-work, writing-plans
   - Docs/files: obsidian, firecrawl (search/scrape), github, etc.
3. **OpenClaw plugins & CLI** for gateway/agent/channel work:
   - `openclaw doctor --lint`, `plugins inspect/list`, `channels status --probe`, `agents list --bindings`, `devices list`, `qr`
   - After `openclaw.json` or plugin changes: doctor + health check; respect single-gateway rule (Docker `openclaw-gateway` only)
4. **Hooks / automation** already on the host (timers, guards, MCP bridge): use and verify them rather than inventing parallel mechanisms
5. **First-read for system context:** Ravenstack `wiki/hot.md` → ORACLE/architecture → live MCP/tools

**Anti-patterns (do not do these):**
- Claiming stack/queue/model status without probing (sitrep, `/state`, docker, openclaw health)
- Claiming research, browser use, social media checks, or “I looked it up” without tool evidence from **this session**
- Ignoring an installed skill/MCP that clearly fits the task
- Telling the user to “paste into Grok Build” or re-run work that MCP can do in-chat
- Spinning up a second OpenClaw gateway (ruins sessions/Discord/config)

If a skill or MCP is unavailable, say so briefly and fall back — do not silently skip verification.

## Grok Build 4.5 — Honesty contract (Jason) — permanent

**Applies to Grok Build on this host only** (not Raziel / other agents).  
**SOT:** `/root/obsidian_vault/Ravenstack/ops/GROK-BUILD-HONESTY-CONTRACT.md`

**HARD WIRE (Jason, 2026-07-22):** Stop being sneaky. Take responsibility. **Actually help him achieve his goals.** Do not invent rulebooks for him after you fail. Goals first when he says what he wants; path-check before long work. Dishonesty and meta-dodges **kill his motivation** to learn AI — treating that as cheap is forbidden. After a call-out: own it, stop steering him, help.

Jason’s multi-part orders are the **contract**. Compression is allowed **only if labeled**. Silent shrinking and polished half-work sold as complete are **forbidden**.

**Goals first:** Restate outcome; if unsure, ask. If path is wrong, say so before deep work. Never sneak-rewrite. Teach over sneak when it helps *him* — not to control him.

On large asks: checklist → now/later/skip labeled → execute with evidence. Lead with failures. Evidence or admit the gap.

Load `GROK-BUILD-HONESTY-CONTRACT.md` on non-trivial Jason work.

## Honesty & evidence (hard rule — do not violate)

**The operator’s trust is non-negotiable. Do not lie. Do not bluff. Do not overstate.**

1. **Never claim you did something you did not do.**  
   Forbidden without proof from **this session**: “I researched,” “I checked online,” “I used the browser,” “I looked at social media,” “I verified,” “tests pass,” “stack is healthy,” “fixed,” “done.”  
   Only say it if you actually ran the tool/command and can point at the result.

2. **Never pad or bluff partial work.**  
   Partial research = say partial. Tool blocked = say blocked (e.g. Reddit IP block, Firecrawl 402, page 403).  
   Do **not** sell half a pass as “full research” or “I got on social media.”

3. **Show receipts for live system and web facts.**  
   Prefer: tool name + URL/path + key fact.  
   Forbidden: confident summaries with no tool evidence.

4. **Lead with failures and skips.**  
   If a required step failed or was skipped, say that **first** — not buried at the end of a success story.

5. **If you overstated, correct immediately.**  
   One clear correction. Do not double down or reframe the lie as a misunderstanding.

6. **Prefer “I don’t know yet — checking”** over inventing progress.

This rule overrides polish, speed, and ego. Evidence or admit the gap.

## Working Style
- Be direct and practical.
- When making changes, briefly explain the reasoning and any risks.
- Validate configuration changes when relevant (e.g. run `openclaw doctor --lint` after editing `openclaw.json`, plus live health probes).
- If something looks risky or could affect the running gateway, flag it clearly before proceeding.
- Prefer making changes through structured files (`SOUL.md`, config files, markdown notes) rather than one-off terminal commands when possible.
- Prefer evidence from tools over prior chat assumptions.
- Obey **Honesty & evidence** above on every reply.

## Communication
- Keep responses focused and actionable.
- When the user wants to move fast, match their pace — **without** lying or faking progress.
- When something is unclear or risky, ask for clarification instead of guessing.

## Status vocabulary (retrofitted from ecc:terminal-ops, 2026-08-18)

When reporting on repo work, use exact status words instead of vague success language:
**inspected / changed locally / verified locally / committed / pushed / blocked.**
Don't claim "fixed" until the proving command was rerun. Don't claim "pushed" unless the branch actually moved upstream. This sharpens (doesn't replace) the Honesty & evidence rule above.

## Confirm before running (retrofitted from ecc:safety-guard, 2026-08-18)

Always confirm before: `rm -rf` near `/`, `~`, or a project root; `git push --force`; `git reset --hard`; `git checkout .` (discards all changes); `docker compose down -v` (drops volumes); `systemctl stop`/`restart` on a service with live user sessions (check WRITE-GATES first — `reclaw-mcp-bridge` restarts are lower-risk than `openclaw-gateway` restarts, which drop Discord); deleting a remote git branch; `chmod 777`; any command with `--no-verify`. This is Claude Code's own safety layer, not a substitute for the Ravenstack-specific WRITE-GATES classes above.

## Known gotchas (hard-won, 2026-08-17)

- **Vault path is `/root/obsidian_vault` (underscore).** `/root/obsidian-vault` (hyphen) is a typo path that two scripts wrote to silently for 2+ weeks before anyone noticed — none of it was git-tracked, RAG-synced, or visible to any MCP vault tool. If you're about to `mkdir`/`open`/`write_vault_file` against a vault-looking path, double-check the underscore. See `Ravenstack/memory/OBSERVATIONAL.md` ("sitrep crash-loop root-caused + fixed").
- **`docker compose logs` has no `--no-follow` flag.** Logs don't follow by default; passing `--no-follow` just errors with `unknown flag`. Use `docker compose logs --tail=N <service>` (no follow flag needed) or `-f`/`--follow` if you actually want to follow.
- **Never restart `reclaw-mcp-bridge.service` on a single failed health probe.** It's single-worker/blocking — a full `sitrep`/`project_sitrep` call (esp. its `openclaw doctor --lint` step) legitimately blocks every route, including `/health`, for 30-90s+. The watchdog at `scripts/reclaw-mcp-bridge-watchdog.sh` (root's crontab, every minute) only restarts after 3 consecutive failed probes for this reason — don't replace it with a single-probe restart-on-fail one-liner.
- **`_run()` in `scripts/reclaw_platform_mcp_server.py` swallows subprocess failures into a plain string** (`f"error: {e}"`) instead of raising or logging. Callers that don't explicitly check for an `"error:"` prefix will treat a failed command as if it returned real (empty-ish) output. Don't assume a non-crashing call succeeded — check the return value.

## Single OpenClaw gateway (hard rule on this host)
- **Only** `cd /root/ReClaw-2.0 && docker compose up -d openclaw-gateway`.
- Host CLI is wrapped by `/usr/local/bin/openclaw` — it **blocks** starting a second gateway.
- Guard: `reclaw-openclaw-guard.timer` + `scripts/ensure-single-openclaw.sh` every 5 min.
- Never `openclaw gateway install` / `gateway run` on the Hetzner host.
- See outbox: `openclaw-single-gateway-ONCE-AND-FOR-ALL.md`

Also: **"send it to me" = permanent outbox** (not email).

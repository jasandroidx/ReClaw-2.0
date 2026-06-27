# AGENTS.md — ReClaw 2.0 Platform Routing & Permissions

**MANDATORY FIRST STEP FOR ANY AGENT/LLM/TOOL**: Load and obey `[[RAVENSTACK-ORACLE.md]]` + `[[RAVENSTACK-ARCHITECTURE.md]]` from the private vault at /root/obsidian_vault/Ravenstack/ (https://github.com/jasandroidx/obsidian-vault). All knowledge in/out MUST go through KnowledgeManager. Never bypass.

This is the operational routing document for the general ReClaw 2.0 platform (with initial rural-data workflow package). It follows the same patterns as the parent winslow-core AGENTS.md in ~/clawd. Core is domain-agnostic; rural_data, grants, local_leads, content and future modules are isolated under agents/.

## Primary Entry Point: Gateway (Control Plane)
- The Gateway (FastAPI in api/main.py or future dedicated gateway/server.py) is the only thing that creates sessions, loads SOUL files + relevant Ravenstack knowledge, and dispatches work.
- All external triggers (Discord bot, cron, manual `python -m reclaw.cli run`, HTTP) go through the Gateway.
- Gateway owns:
  - Session creation + isolation (data/sessions/<id>/)
  - Loading the system SOUL.md + the relevant agent SOUL.md(s) + targeted knowledge from `core/knowledge.py` (e.g. principles + domain files)
  - Permission registry + approval gate enforcement (add `knowledge_read` as low-risk capability)
  - Status tracking and artifact collection
  - Calling the Orchestrator for full pipeline runs

## Current Agent Roster (MVP — rural_data module)

**Note:** This is the first concrete domain module (rural_data). Core platform (Gateway, Session, Security, events) is domain-agnostic. Future domains (grants, local_leads, content, research_packets, visual_office) follow the same structure under agents/<domain>/.

### researcher (rural_data)
- **SOUL:** agents/researcher/SOUL.md
- **Mission:** Harvest public county data into a validated ResearchPackage.
- **Capabilities (declared skills):**
  - public_data_seed (low risk, always allowed)
  - public_data_live_fetch (medium-high risk — requires approval gate unless session has `live_fetch_approved: true`)
- **Inputs:** county, primary_area, optional force_seed
- **Outputs:** ResearchPackage (written to session/handoffs/research.json)
- **Handoff target:** analyst or orchestrator

### analyst (rural_data)
- **SOUL:** agents/analyst/SOUL.md
- **Mission:** Convert ResearchPackage into practical insights + red flags + channel-ready angles.
- **Capabilities:**
  - heuristic_analysis (low risk)
  - llm_synthesis (future, high risk — will require model access gate + cost tracking)
- **Inputs:** ResearchPackage (from handoff or session path)
- **Outputs:** AnalysisPackage (session/handoffs/analysis.json)
- **Handoff target:** orchestrator

### orchestrator (light)
- **Mission:** Sequence the pipeline, enforce quality gates, assemble ContentPackage, decide on publication, invoke channel writers.
- **Capabilities:**
  - pipeline_control (medium)
  - obsidian_publish (medium — writes directly to vault path)
- **Quality Gates it enforces (see SOUL.md):**
  1. Research has sufficient data
  2. Analysis has red flags or strong insights
  3. Risk score + manual override logic
- **Outputs:** ContentPackage + sidecar JSON + Obsidian .md

### clawforge (meta - visual floor compiler)
- **SOUL:** agents/clawsmith/SOUL.md (updated for CellBlueprint)
- **Mission:** Top-level meta-agent after Boss. Compiles plain-English rural income goals into persistent themed cells (Grant Hall etc.) under ~/.openclaw/workspace/rooms/. Prunes workers, writes SOUL/AGENTS.md + Total-ReClaw memory, registers gates, emits WS visual events for 2D dashboard. Enforces ReClaw principles on Hetzner (Docker volumes, Tailscale WS, GPU vec).
- **Capabilities:** cell_create, visual_event_emit, grant_scan, compliance_audit, memory_consolidate (all gated).
- **Outputs:** CellBlueprint + ForgePackage to Obsidian/Rooms + room folder with memory.db.
- **Visual:** Updates static pixel sprites on dashboard (Grant Hall FUNDING TRACKER etc.).

## Routing Rules (Gateway decides)
- "Run Pike Winslow research package" (or any domain trigger) → full pipeline via Orchestrator (default happy path for rural_data module)
- "Just harvest data for Pike" → researcher only (rural_data), return ResearchPackage JSON, no Obsidian write
- "Re-analyze existing research <id>" → load from runs/ or session, run analyst only
- "Re-export package <id> to Obsidian" → load package, call writer (bypass gates if already approved)
- Future: "Audit GBP for Smith Auto" → will route to grants or local_leads domain (parallel tree sharing core Gateway/Security/Session)

If the task is ambiguous, Gateway creates a session, loads context, and asks for clarification (or writes a decision request to the session log for human).

## Handoff Protocol (Strict — same as parent OpenClaw)
1. Gateway prepares a self-contained session:
   - Copies or symlinks relevant SOUL.md excerpts
   - Writes task.json with county, goals, constraints, permission grants for this session
   - Creates handoffs/ and logs/ dirs
2. Agent is invoked (in-process for now, later possibly separate container or process with restricted FS).
3. Agent reads only from its allowed paths in the session.
4. Agent writes its output package as JSON to handoffs/<agent>-output.json + appends to session.log
5. Agent returns a tiny status (success | partial | failed) + any escalation notes.
6. Gateway (or Orchestrator) reads the handoff, validates, updates session state, decides next route or quality gate pass/fail.
7. All durable state ends up in data/runs/ + the Obsidian vault.

Never rely on Python object memory between agents. The JSON on disk is the truth.

## Permission & Approval Gate System (Security Core)
Every capability has a risk level declared in the agent's code / manifest.

- **low**: auto-granted in every session (read seeds, write to own handoff dir)
- **medium**: logged + auto-granted for known good counties, or requires one-time per-session approval
- **high**: always requires explicit approval. Examples:
  - live web fetch / browser on a new county domain
  - any shell execution
  - writing outside the session dir or the approved obsidian subdir
  - loading a new LLM model or spending tokens

**How gates work (MVP implementation):**
- When an agent wants a high-risk action, it calls `request_approval("live_fetch", reason="need fresh 2026 budget PDF for Pike auditor")`
- The permission system writes `approvals/pending-live_fetch-<ts>.json` into the session.
- If the session was started with `--auto-approve` or the Gateway has a pre-approved list for this county, it grants.
- Otherwise: for CLI runs, prompt the human; for API runs, mark "awaiting_approval" and return 202 + the pending request id. Human (or future Discord bot) approves via a later API call or by writing an approved file.
- Approved grants are recorded in session/approvals/granted-*.json and attached to the final package provenance.

This is the "strong security by default" requirement.

See core/security.py (to be implemented) and docs/SECURITY.md for exact gate examples and how Docker volumes are mounted read-only where possible.

## Explicit Permissions for Current MVP
For a standard rural_data ("Pike Winslow") daily run (first domain):
- researcher: seed read = allowed, live_fetch = medium (default off unless .env USE_LIVE_FETCH or per-session grant)
- analyst: heuristic only = allowed
- orchestrator: write to configured obsidian_vault_path = allowed (the path is the only place it can write final artifacts)
- No shell access for any agent in MVP.

Core platform capabilities (Gateway, Security, Session, events) are shared across all domains.

## Failure & Escalation
- Agent produces invalid JSON or fails schema validation → Gateway aborts the session, writes failure log, does not publish.
- Hallucinated numbers in research (detected by cross-check or human) → session marked "needs_human_review", package goes to a quarantine/ folder in Obsidian or runs/quarantine/.
- Violates SOUL → immediate abort, write violation to session + append to daily memory log in parent clawd if linked.
- Cost or time overrun → Orchestrator can kill the session and report.

## Adding a New Agent Later
1. mkdir -p agents/scriptwriter
2. Write agents/scriptwriter/SOUL.md (load the ContentPackage spec + channel voice from parent docs)
3. Implement the agent class that reads handoff JSON, writes its output JSON.
4. Register the agent + its declared skills + risk levels in gateway/permission_registry.py
5. Add routing rule in AGENTS.md
6. Update docker-compose if it needs extra GPU slices or different image.
7. Test with a full pipeline that includes the new handoff.

## Daily / Cron Usage
The Gateway exposes /trigger or the CLI `python -m reclaw run --county Pike --area Winslow`
A simple cron or systemd timer on Hetzner calls it daily for the primary counties.
Output always lands in Obsidian so the human (Boyd) sees it on next vault sync without needing to SSH.

This document + SOUL.md + the per-agent SOULs are the contract. Code must implement the spirit, not just the letter.

## Clawsmith / Clawforge (Meta-Compiler for visual_office & project rooms)
- **Skill:** `/root/.openclaw/workspace/skills/clawsmith/SKILL.md` (trigger: "forge a room", "clawsmith business goal", "create openclaw project room", "bootstrap visual castle office").
- **Mission:** Clawforge the Blacksmith (*CLANG*) analyzes goal complexity to size rooms (Tier 1=single specialist vs Tier 2+=coordinator + specialists + sub-agents per parallel lanes). Forges full structural configs: AGENTS.md coordinator, specialist SKILL.md (hybrid frontmatter, Context/Operational Steps with exact commands/pending_approval gates/Error Handling), Obsidian vault manifest + castle_map.json (for visual square/pixel "offices" with anvils/forges), deploy.sh.
- **Key Guarantees:** Sandbox (env vars only, no hardcoded keys/logs), mandatory human approval gates for *any* external write (email, git, API, outreach → pending_approval in vault + notification), ReClaw Pydantic handoffs, tight well-oiled machine (boundaries, heartbeats, escalation). Biases toward rural_data, SEO, marketplace automations.
- **Integration:** `python3 /opt/reclaw/tools/clawsmith.py --goal "Your goal" [--output-dir ./room]`. Run generated deploy.sh. Reloads into OpenClaw workspace. Directly enables the badass castle/forge visual UI (main orchestrator oversees pixel agents hammering in office squares).
- **Location in repo:** /opt/reclaw/tools/clawsmith.py + skill in workspace. Part of visual_office future domain.

Add routing in gateway/permission_registry.py if needed for auto-approval levels (low-risk forging).

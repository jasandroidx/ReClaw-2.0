# SECURITY.md — ReClaw 2.0 (Least Privilege + Approval Gates)

This document explains the security model and how to operate it safely on Hetzner (production) and local dev.

## Philosophy (inherited from OpenClaw + Winslow SOUL)
- Agents get the absolute minimum power needed for their job.
- High-risk actions (anything that touches the real world outside the session sandbox or spends money/tokens) require an explicit, auditable approval for that session.
- The Gateway is the only trusted actor that can grant power.
- Everything is logged to disk in the session so you can later answer "who approved the live scrape on June 12 and why?"

## Risk Levels
- **low**: Read seeds, run heuristics, write inside session/handoffs. Auto-granted.
- **medium**: Live HTTP to known .gov sites, writing final artifacts to the Obsidian vault path. Usually auto-granted for the primary counties we trust, or granted at session start.
- **high**: Shell execution, browser automation that can be steered to arbitrary sites, loading new models that cost $, writing anywhere else on disk. Almost never auto-granted.

Current declared capabilities are in `core/security.py:DECLARED_CAPABILITIES`.

## How Approval Gates Work (MVP)
1. Agent code calls `security.request_approval("public_data_live_fetch", reason=...)`
2. This writes `data/sessions/<sid>/approvals/pending-<id>.json`
3. SecurityManager.is_granted(...) returns False → agent falls back to seed or aborts the step.
4. Human (or bot) calls `POST /sessions/<sid>/approve?capability=public_data_live_fetch&granted_by=discord:boyd`
5. Grant is written to `approvals/granted/<grant-id>.json`
6. Subsequent (or retried) agent code sees the grant and proceeds. The action is also logged to `logs/security.log`

For cron / fully automatic runs on Hetzner you will usually start the trigger with `auto_approve=true` **only for the counties and capabilities you have explicitly whitelisted** (see Gateway code).

## Docker Sandboxing Recommendations (Hetzner)
In docker-compose.yml we currently use a standard python slim image.

Hardening steps you can add later (without changing much code):

- Run the reclaw-api container as non-root (already done in Dockerfile).
- Mount the code read-only where possible: `:ro`
- Mount only specific volumes:
  - `data:/app/data` (sessions + runs + seeds)
  - The obsidian export dir (write-only for the final writer)
- Use `--read-only` + `--tmpfs /tmp` for the container.
- For future separate agent workers: give them even tighter mounts (only their session dir + read-only seeds).
- seccomp / AppArmor profiles if you run anything that does browser work.
- No NET_ADMIN or other caps.

The current `docker-compose.yml` has a commented GPU section as example.

## Tailscale + Exposure
- Never publish port 8000 on the public internet.
- Use `ports: ["127.0.0.1:8000:8000"]` (already in compose).
- Access only from your Tailscale IP or via `tailscale serve`.
- The Gateway can (and should) require a simple bearer token in prod (add in a follow-up).

## What the Researcher Is Allowed to Do Today
- Always: read `data/seeds/`
- With grant or auto_approve: make HTTP GETs to county sites you have reviewed (start with your own county .gov and auditor sites).
- Never (in MVP): POST, logins, or following arbitrary links returned in HTML.

## Incident Response
If something looks wrong:
1. `ls data/sessions/` — find the bad session
2. `cat data/sessions/<sid>/logs/session.log`
3. `cat data/sessions/<sid>/approvals/pending*` and `granted/*`
4. `cat data/runs/*<pkg-id>*.json`
5. Quarantine the Obsidian file if it was published (`mv` it to a `quarantine/` subdir in the vault and note the reason).

Then fix the gate or the agent code and re-run with tighter constraints.

## Future Hardening (when adding Scriptwriter / business agents)
- Separate capability namespaces (e.g. `business:gbp_audit`, `business:write_review_reply`)
- Per-agent token / identity when we split processes
- Cost tracking + daily spend caps on any LLM calls
- Human-in-the-loop gate for any client-facing output (GBP posts, emails)

This model has kept the parent OpenClaw workspace safe while running on a single rural Hetzner box. ReClaw inherits it.

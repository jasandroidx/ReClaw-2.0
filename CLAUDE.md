# ReClaw 2.0 — the Ravenstack engine

FastAPI service, agent swarm, county audit pipeline, and the MCP server that
exposes all of it. "ReClaw" is the plumbing's name; the project is Ravenstack.

## Read first

`RAVENSTACK.md` in this repo is an enforcement layer that defers to two files
in the private vault (`jasandroidx/obsidian-vault`, mounted at
`/root/obsidian_vault` in production):

    Ravenstack/RAVENSTACK-ORACLE.md
    Ravenstack/RAVENSTACK-ARCHITECTURE.md

Those define knowledge structure, naming, frontmatter, links and tags for
anything written to the vault. Load them before any ingest, distill or publish.
`SOUL.md` carries the non-negotiables; the ones that bite most often:

- **Truth above comfort.** Every claim carries a source. If there is no sourced
  answer, say so rather than producing a plausible one.
- **Least privilege + approval gates.** Dangerous actions declare themselves
  and block on a human for that session.
- **Session isolation.** Every run gets its own workspace under
  `data/sessions/`. No cross-talk except through explicit handoff JSON.
- **Offline first.** Everything must work from seeds. Live fetches are a bonus,
  never a dependency.

## Hazards — all of these have already caused real damage

- **This repo is PUBLIC.** Never commit a key, token, or the Tailscale Funnel
  path (an unauthenticated bearer secret). The funnel path is read from
  `MCP_FUNNEL_PATH`; it was previously hardcoded in five places and nearly
  published.
- **Production runs uncommitted code.** The Hetzner box sits on branch
  `backup-2026-07-07` with a dirty tree. `scripts/reclaw_platform_mcp_server.py`
  had ~1,350 lines existing nowhere else. Run `git status` before any
  `checkout`, `reset`, `restore`, `clean` or `stash` there. A careless checkout
  destroys work that has no other copy.
- **The vault path is `/root/obsidian_vault` — underscore, not hyphen.**
  `/root/obsidian-vault` is a decoy created by a typo'd `os.makedirs`. Two cron
  scripts wrote weekly audits into it for months and nothing reached the vault.
- **The county queue is frozen on purpose.** `data/content_truth_rules.yaml`
  has `status: freeze_county_mill`, because Gateway's `ent_name` field does not
  support vendor-fraud claims. Do not run `county-queue/run-next` to "unblock"
  anything. Unfreezing is a human decision.
- **Never call `project_sitrep`, `sitrep`, or `github_gap_suggestions`.** They
  are synchronous mega-handlers that self-probe port 8100 and hang 60s+
  returning nothing. Use `stack_health`, `pipeline_status`, `pending_gates`.

## Layout

    api/main.py          FastAPI on :8000 — the operational truth
    core/                config, county_queue, job_registry, security, session
    agents/              researcher, auditor, analyst, content studio
    scripts/
      reclaw_platform_mcp_server.py    MCP server (:8100 streamable-http)
      reclaw_platform_mcp_extensions.py  the Tier A–D operator tools
    data/                queue state, sessions, runs, caches, YAML rulebooks
    dashboard/index.html Command Center (:8081)
    dashboard/ravenstack-fortress/     Next.js agent-town fork — SEPARATE APP

## Key endpoints

    GET  /state                    everything at once: queue, jobs, gates
    GET  /county-queue/status
    POST /county-queue/approve     human gate
    POST /county-queue/reject      reason required, logged to lessons ledger
    POST /sessions/{id}/approve    grant a blocked capability
    POST /ingest                   PDF -> distilled note -> vault -> RAG
    POST /trigger/{county}

The Keep (`jasandroidx/ravenstack-keep`, `:8120`) reaches these through an
allow-listed proxy at `/api/reclaw/*`. It is not a general proxy — keep it
narrow.

## Rules

- A reject needs a real reason. It is written to `data/auditor_lessons_log.yaml`
  and shapes the next run.
- Do not approve a gate to make a flow complete. The gate is the product.
- Record mistakes in `data/auditor_lessons_log.yaml` with symptom, root cause
  and the rule that follows. That ledger is why the pipeline stopped publishing
  unsupported claims.

## Checks

    python3 -m py_compile api/main.py scripts/reclaw_platform_mcp_server.py
    docker compose ps
    curl -sf localhost:8000/health

---
name: ravenstack-sitrep
description: "Live Fortress status: sitrep, stack health, queue, morning check."
---

# Fortress Sitrep — full live status

**Core principle:** Always probe live. Never invent health. **Fortress** = entire stack
(OpenClaw + ReClaw + repo + Ravenstack + Docker + Tailscale + MCP + nodes).

**REQUIRED:** Call tools **this turn**. Prior sitrep text is not truth.

## HARD RULES

1. **Never call `project_sitrep`, `sitrep`, or `github_gap_suggestions`.** Verified
   2026-08-15 and 2026-09-03: they hang 60s+ and **return nothing**. Synchronous
   mega-handlers on a single-worker server that self-probe :8100 from inside a request
   that server is already serving.
2. **Never run `scripts/post-deploy-healthcheck.sh` as an MCP fallback.** It runs
   `openclaw mcp list` and can **deadlock** the single-worker server on :8100. The
   fallback for "MCP is down" must not be capable of taking MCP down.
3. Read the false alarms below BEFORE scoring anything.
4. No mutations. No pipeline runs, approvals, or writes unless asked after.

## Canonical facts — verify live, never from a doc

Source of truth: `/root/obsidian_vault/Ravenstack/ops/incidents/INDEX.md`

- Live MCP unit: **`reclaw-platform-mcp.service`** (NOT `reclaw-mcp-bridge`)
- Tailnet IP: **`100.85.152.115`** (`100.108.130.82` is dead)
- Repo branch: **`main`** (docs saying `ravenstack` are wrong)
- Outbox: `https://openclaw.tail20a090.ts.net:8765/`
- Serve is HTTPS — never plain `http://100.x:port`

## Known false alarms — do NOT report these as outages

| Reads as | Actually |
|---|---|
| `mcp_bridge_unit: inactive` | Probe checks a renamed unit. Confirm `systemctl is-active reclaw-platform-mcp`. |
| `mcp_tunnel_unit: inactive` | By design — quick tunnel disabled, public plane is Tailscale Funnel. |
| `public_health_http: 000` | Self-probe deadlock. Verify from off-box. |
| `dashboard_status` mcp down / PARTIAL | Same self-probe bug. If any tool answered, MCP is up. |
| Pending `compliance_audit` gate | Real unanswered request — HIGH risk, deliberately not auto-granted. Open decision, not breakage. |
| PID on :8100 changed | Cron watchdog restarted it, likely tripped by your own tool burst. |

## Procedure

Call these **six in one parallel batch**:

`stack_health` · `pipeline_status` · `pending_gates` · `git_vault_status` ·
`dashboard_status` · `connector_status`

Fill holes only if one fails: `docker_status`, `openclaw_health`, `reclaw_health`,
`openclaw_models`, `inspect_session`.

Fire the batch **once**. Re-firing to "double-check" is what trips the watchdog.

## Shell fallback (MCP genuinely down only)

```bash
cd /root/ReClaw-2.0
docker compose ps
systemctl is-active reclaw-platform-mcp
ss -ltnp | grep 8100
tailscale status | head
curl -sf -m 5 http://127.0.0.1:8000/health
curl -sf -m 5 http://127.0.0.1:18789/health || true
```

Mark the report **DEGRADED (shell fallback)**.

## Output

1. One-line verdict with UTC timestamp
2. What is broken — RED/AMBER only, each with the tool output proving it
3. Top blockers + one next action
4. Green roll-up in a single line

Do not dump raw JSON. Do not table everything that is fine.

## After sitrep (only if asked)

| Ask | Action |
|-----|--------|
| Save to vault | `write_vault_file` under `Ravenstack/ops/` |
| Fix what's broken | Hand off to **`openclaw-mechanic`** |
| Approve queue / run pipeline | Explicit human intent only — county is FROZEN |

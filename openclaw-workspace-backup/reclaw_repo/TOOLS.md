---
summary: "Workspace template for TOOLS.md"
title: "TOOLS.md template"
read_when:
  - Bootstrapping a workspace manually
---

# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## Related

- [Agent workspace](/concepts/agent-workspace)

## ReClaw Engine Connection (minimum foundation)

Execution engine: /opt/reclaw (companion only; do not treat as part of this agent).

Gateway (current): http://${RECLAW_GATEWAY_HOST:-host.docker.internal}:8000 (published from its docker-compose; also available over Tailscale via the host). Use host.docker.internal when the agent runs inside OpenClaw's container (its compose adds the host-gateway alias); override with RECLAW_GATEWAY_HOST=127.0.0.1 when testing the script directly on the host.

### Tiny demo workflow (the one path for this foundation step)
```bash
cd /root/.openclaw/workspace
./tools/reclaw-rural-demo
```
Defaults to safe read-only (health + current vault state + the exact command for a real run). Pass `--execute` only when you want it to actually trigger a seed-based rural_data package.

### Real rural_data invocation (seed-only, blocking, writes to vault)
```bash
curl -s -X POST 'http://${RECLAW_GATEWAY_HOST:-host.docker.internal}:8000/run-sync?county=Pike&area=Winslow&write_obsidian=true' | python3 -m json.tool
```

After success the response contains `obsidian_file`, `risk_score`, `package_id`. The .md + sidecar .json are written by ReClaw to:
`/root/obsidian_vault/Rural Data/<date>-pike-winslow.md` (and .json)

(This is the min vault/output path wiring — no ReClaw code was changed; its compose already does `- /root/obsidian_vault:/vault` + env override.)

### Token note (for future /trigger use)
Production triggers use `Authorization: Bearer <token>`. The token lives in `/opt/reclaw/.env` as `RECLAW_GATEWAY_TOKEN`. Reference the file; never paste the raw value into logs, chat, or this workspace.

After any run: update the daily memory file here in the workspace with facts from the result + vault artifact. Your agent memory and rules stay in this workspace.

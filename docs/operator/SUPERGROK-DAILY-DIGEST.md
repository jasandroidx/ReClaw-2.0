# SuperGrok Daily Fortress Digest

**Phase B** · Report-only · You always approve mutations  
**Status:** Implemented on server (tools + docs) · **You** still create the SuperGrok Automation in the UI

## Schedule

- **When:** Morning America/Chicago (pick 7:00–9:00 local in SuperGrok Automations)
- **Where:** SuperGrok → Automations / Tasks
- **Connector:** ReClaw Platform MCP must be **on** for the task (same URL as chat, path ends `/mcp`)

## Setup (once) — YOU do this in SuperGrok UI

1. Open SuperGrok → **Automations** (or Tasks).
2. **New automation** · Schedule: daily morning US.
3. Enable **ReClaw / reclaw-platform** connector for this automation if the UI has a connector picker.
4. Paste the entire contents of `docs/operator/prompts/morning-fortress-digest.txt` as the task prompt  
   (or ask SuperGrok: `Call read_repo_file with relative_path "docs/operator/prompts/morning-fortress-digest.txt"`).
5. Enable push/email **if** SuperGrok offers it; otherwise open Automations history each morning (acceptable).
6. Run **once manually** to verify all six headings appear.

## Preferred tools (live server)

| Priority | Tool | Role |
|----------|------|------|
| 1 | `morning_digest` | One-shot Phase B digest |
| 2 | `project_sitrep` | Full fortress status |
| 3 | `pipeline_status` / `county_queue_card` | Queue detail |
| 4 | `public_mcp_url` / `connector_status` | Tunnel URL after rotate |

## If the connector fails

On the server (or ask Grok Build):

```bash
cat /root/ReClaw-2.0/data/mcp_public_url.txt
curl -sf http://127.0.0.1:8100/health
systemctl is-active reclaw-mcp-bridge reclaw-mcp-tunnel
```

Update SuperGrok connector URL if the trycloudflare host rotated. Prefer Tailscale when possible.

## Digest shape (required)

1. Overall  
2. Stack (Docker / API / OpenClaw / MCP)  
3. County queue  
4. OpenClaw / models  
5. Gaps  
6. Actions (+ SUGGESTED auto-actions require human OK)

## Never in this automation

- Approve/reject county queue  
- `run_pike_winslow` / `county_queue_run_next`  
- Vault writes  
- `file_github_gaps`  
- Docker restarts  
- Fake/simulated sitrep  

## After you approve a suggestion

In SuperGrok chat (not the silent automation), e.g.:

- “Call county_queue_card and summarize Gibson”
- “Approve Gibson county queue” → then agent uses `county_queue_approve(confirm=true)`
- “File GitHub issues for sitrep gaps” → `file_github_gaps(confirm=true)`

## Smoke test (server)

```bash
/root/ReClaw-2.0/.venv/bin/python /root/ReClaw-2.0/scripts/smoke_morning_digest.py
```

## Related

- Spec: `docs/superpowers/specs/2026-07-10-supergrok-daily-operator-digest-design.md`
- Prompt: `docs/operator/prompts/morning-fortress-digest.txt`
- Vault: `Ravenstack/supergrok-daily-digest.md`
- Roadmap: `docs/operator/ROADMAP-PRACTICAL.md`

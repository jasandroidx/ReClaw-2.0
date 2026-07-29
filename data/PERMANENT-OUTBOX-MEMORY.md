# PERMANENT MEMORY — Operator Outbox

## The only outbox URL

**http://100.108.130.82:8765/**

| Fact | Value |
|------|--------|
| URL | `http://100.108.130.82:8765/` |
| Bind | Tailscale IP only (`100.108.130.82:8765`) |
| Directory | `/root/outbox` |
| Service | `reclaw-outbox.service` → `/usr/local/bin/reclaw-outbox-serve` |
| Access | Tailscale; not public internet |
| Index | `/root/outbox/index.html` (curated home — update when adding important files) |

## Agent rule (non-negotiable)

When producing anything Jason will open on phone/desktop:

1. Write the file under **`/root/outbox/`**
2. **Link it on `index.html` in the top card** if it is “start here” material (not only append at bottom)
3. Tell the user the full URL: `http://100.108.130.82:8765/<filename>`
4. Prefer `.html` with big links for phone when the deliverable is a checklist/prompt

Do **not** only leave files in chat, vault-only, or `/tmp` and call it delivered.

## Current focus pack (2026-07-17)

- http://100.108.130.82:8765/NEW-CHAT-PROMPT-silent-auditor.html
- http://100.108.130.82:8765/SESSION-START-silent-auditor-2026-07-17.md
- http://100.108.130.82:8765/auditor-pipeline-e2e-research-2026-07-17.md
- http://100.108.130.82:8765/GEMINI-DEEP-RESEARCH-auditor-pipeline-PROMPT.md

## Related durable copies

- Vault: `Ravenstack/ops/` (secondary; outbox is primary for “go get it”)
- This note also mirrored in vault as permanent operator memory

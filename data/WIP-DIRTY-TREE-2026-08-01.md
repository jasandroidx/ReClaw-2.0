# ReClaw dirty tree WIP — 2026-08-01

**Branch:** backup-2026-07-07 (tracking origin/backup-2026-07-07)  
**Intent:** Document residual Phase 0 dirties without force-push or mixed secret commits.

## Dirty / untracked (snapshot)

- M AGENTS.md, CLAUDE.md, MEMORY.md, data/PERMANENT-OUTBOX-MEMORY.md
- ?? .grok/skills/county-video-shorts/
- ?? data/upwork_digests/2026-07-29.md, 2026-07-31.md

## Policy

- Do not commit secrets or .env.
- Digests and memory may be committed in a focused PR later.
- Production OpenClaw config lives under /root/.openclaw (not this repo tree dirty list above).
- Free model profile applied 2026-07-31; stamp: /root/.openclaw/ravenstack-model-profile.json

## Next operator action

Review and commit digests separately if desired; keep backup-2026-07-07 until explicit merge strategy.

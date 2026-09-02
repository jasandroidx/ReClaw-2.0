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
| Index | `/root/outbox/index.html` (**curated home — THIS is what Jason opens**) |
| Publisher | `/usr/local/bin/outbox-publish` |

## Why Jason keeps saying “it’s not on the web outbox”

**Root cause (2026-07-29 lesson):** Agents wrote files into `/root/outbox/` and reported success. Python `http.server` **did** serve the direct URL (HTTP 200). But Jason opens **`index.html`**, which is a **curated** home page — **not** an auto-directory listing of every file. Unlinked files are invisible from the home page.

**Fix forever:** after writing any operator deliverable, run:

```bash
outbox-publish /root/outbox/YOUR-FILE.md --title "Human-readable label"
```

That copies if needed, injects a link at the **top** of the green “What you asked for (now)” card, and prints the full URL.

## Agent rule (non-negotiable)

When producing anything Jason will open on phone/desktop:

1. Write the file under **`/root/outbox/`**
2. Run **`outbox-publish … --title "…"`** (or manually link on `index.html` top card)
3. Tell the user:
   - Home: `http://100.108.130.82:8765/`
   - Direct: `http://100.108.130.82:8765/<filename>`
4. Prefer `.html` with big type for phone when the deliverable is a checklist/prompt/script
5. Smoke-check: `curl -sS -o /dev/null -w '%{http_code}\n' http://100.108.130.82:8765/<filename>` → expect `200`

### NOT done if any of these are true

- File only in chat, vault, `/tmp`, or repo without outbox copy
- File in `/root/outbox` but **not** on `index.html` top card
- You said “it’s in the outbox” without giving the home + direct URLs

## Current hot deliverable (2026-07-29)

- http://100.108.130.82:8765/2026-07-29-PIKE-COUNTY-INTERESTING-FACTS-REVIEW-CARD.html
- http://100.108.130.82:8765/2026-07-29-PIKE-COUNTY-INTERESTING-FACTS-REVIEW-CARD.md

## Related durable copies

- Vault: `Ravenstack/ops/PERMANENT-OUTBOX-MEMORY.md` · `Ravenstack/ops/OUTBOX.md`
- Repo: `ReClaw-2.0/data/PERMANENT-OUTBOX-MEMORY.md` · `CLAUDE.md` · `MEMORY.md`

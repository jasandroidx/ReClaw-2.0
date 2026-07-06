# Obsidian as Source of Truth — ReClaw Connection Guide

The production vault lives at **`/root/obsidian_vault`** on Hetzner (git-backed).

---

## How ReClaw connects TODAY (server — no Obsidian app required)

| Layer | What it does |
|-------|----------------|
| **`tools/obsidian_bridge.py`** | Pipeline writes package + audit supplement + county index |
| **`core/obsidian_writer.py`** | Renders ContentPackage → `Rural Data/YYYY-MM-DD-county-area.md` |
| **`reclaw-platform` MCP** | `read_vault_file` / `write_vault_file` for agent edits |
| **`reclaw-fs` MCP** | Direct filesystem read/write on vault path |
| **Docker mount** | `/root/obsidian_vault` → `/vault` in reclaw-api container |

### Every county audit run writes:

1. `Rural Data/{date}-{county}-{area}.md` — full content package
2. `Rural Data/{date}-{county}-{area}.json` — sidecar data
3. `Rural Data/{date}-{county}-audit-flags.md` — red flags by category
4. `Rural Data/County Audit Index.md` — MOC table of all counties audited
5. `Rural Data/_latest.md` — pointer to newest package

### Required `.env` (must use `RECLAW_` prefix):

```bash
RECLAW_OBSIDIAN_VAULT_PATH=/root/obsidian_vault
RECLAW_OBSIDIAN_SUBDIR=Rural Data
```

### Health check:

```bash
cd /root/ReClaw-2.0
PYTHONPATH=. .venv/bin/python -c "from tools.obsidian_bridge import vault_health; print(vault_health())"
```

---

## Why `obsidian-mcp-server` is disabled on Hetzner

That MCP talks to **Obsidian desktop** via the **Local REST API** plugin (`http://127.0.0.1:27123`). It does not read vault files directly.

- Server has the vault files ✅
- Server does not run Obsidian app ❌

**Use reclaw-platform vault tools instead** — same result for automation.

---

## Connecting your Windows Obsidian app (optional, for editing)

Your PC Obsidian and Hetzner vault can stay in sync:

| Method | Best for |
|--------|----------|
| **Git** | Vault already has `.git` — pull on PC after server pushes |
| **Syncthing** | Real-time two-way sync |
| **SSHFS / Tailscale** | Mount Hetzner vault as network drive |

### Optional: Local REST API on your PC

If you want `obsidian-mcp-server` from Cursor on Windows:

1. Install [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) in Obsidian
2. Copy API key → `OBSIDIAN_API_KEY` in local config
3. Enable HTTP on port 27123
4. Point MCP at your PC (not Hetzner)

On Hetzner, keep using `obsidian_bridge` + `reclaw-platform`.

---

## RAG sync (search your vault from the agent)

```bash
# Via MCP
reclaw-platform__rag_sync_vault

# Or API
curl -X POST http://127.0.0.1:8000/rag/sync-vault
```

Indexes `Ravenstack/` + vault notes for `query_knowledge` citations in scripts.

---

## Vault layout

```
/root/obsidian_vault/
├── Rural Data/           ← county audit packages (faceless YT)
│   ├── County Audit Index.md
│   ├── 2026-07-06-spencer-spencer.md
│   └── 2026-07-06-spencer-audit-flags.md
├── Ravenstack/           ← ORACLE, architecture, backlog
└── Rooms/                ← agent forge notes
```

---

## Fix later (backlog — do not block auditor work)

Tracked in `data/obsidian_fix_backlog.yaml`. Current pipeline works via filesystem; these are enhancements.

| Priority | Item | Why later |
|----------|------|-----------|
| P1 | **Docker API vault path** — confirm `reclaw-api` container has `RECLAW_OBSIDIAN_VAULT_PATH=/vault` after `.env` fix; restart compose if `/run-sync` still writes Pike defaults | Host `.env` fixed; container may need bounce |
| P1 | **PC ↔ Hetzner sync** — choose git-pull vs Syncthing so Jason's Obsidian app sees `Rural Data/` in real time | Requires your machine setup |
| P2 | **obsidian-mcp-server on Windows** — Local REST API plugin + `OBSIDIAN_API_KEY` in Cursor local config | Only for editing from PC; server uses bridge |
| P2 | **Auto RAG sync** — call `rag_sync_vault` after each county publish | Not wired in orchestrator yet |
| P2 | **`obsidian_filename` null** in some session JSON — ensure ContentPackage always sets filename before handoff | Cosmetic / county-queue links |
| P3 | **Omnisearch** — install community plugin for BM25 vault search via obsidian MCP | Optional; reclaw-platform RAG covers most |
| P3 | **Dataview queries** — add template queries to County Audit Index for risk/flag sorting | Polish |

### Resume checklist (when you're ready)

```bash
# 1. Verify vault writes land correctly
cd /root/ReClaw-2.0 && PYTHONPATH=. .venv/bin/python -c "from tools.obsidian_bridge import vault_health; print(vault_health())"

# 2. Bounce API if docker still pointed at outputs/obsidian
cd /root/ReClaw-2.0 && docker compose restart reclaw-api 2>/dev/null || true

# 3. On Windows Obsidian: git pull obsidian-vault repo (or Syncthing)

# 4. Optional PC MCP: install Local REST API → set OBSIDIAN_API_KEY → enable obsidian in config.toml
```

### What already works (don't re-fix)

- `tools/obsidian_bridge.py` — package + audit-flags + index
- `RECLAW_OBSIDIAN_VAULT_PATH=/root/obsidian_vault` in host `.env`
- Vault git push to `jasandroidx/obsidian-vault`
- `reclaw-platform__read_vault_file` / `write_vault_file`
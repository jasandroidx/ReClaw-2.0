# RAVENSTACK — MANDATORY KNOWLEDGE HUB (READ THIS FIRST)

**This is the single source of truth for all agents, LLMs, and tools.**

Private Obsidian vault (SOT): https://github.com/jasandroidx/obsidian-vault (ravenstack branch)
Local path on this machine: /root/obsidian_vault/Ravenstack/

**EVERY interaction with knowledge MUST go through:**
- `core/knowledge.py` → `KnowledgeManager`
- `RAVENSTACK-ORACLE.md` (the rule set / instruction book)
- `RAVENSTACK-ARCHITECTURE.md`

**Never** read or write directly to the vault. Never ignore this file.

The Oracle + Architecture files define:
- Where to save (always distilled, through KnowledgeManager or ingest skill)
- Where to look (targeted sections only)
- Naming, formatting, and distillation rules
- Reload ritual
- MCP connector expectations

**Current single OpenClaw install**: /root/openclaw (docker compose up -d)

Any new session or agent must load the Oracle first. This file exists so no future AI or tool can miss the private Ravenstack hub.
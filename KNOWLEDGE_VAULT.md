# ReClaw Knowledge Vault & Document Ingest

**Phase C Complete** — Simple daily workflow for slamming PDFs, books, research papers, and knowledge into your Obsidian vault with smart extraction, organization, and instant RAG search.

## Goal
Drop local files (or folders) from your computer → kimi-claw extracts the highest-value information → clean, tagged Markdown notes land in your Obsidian vault → immediately searchable in RAG dashboard + Fortress Knowledge Vault chamber + future agents.

## Quick Daily Workflow (Choose One)

### Option 1: RAG Dashboard (Recommended for most uploads)
1. Open: https://vb2sxll3shzgg.kimi.page
2. Use the **Import File** button or drag & drop your PDF/book directly onto the page.
3. (Optional) Add a short prompt like: "Ingest this into the Knowledge Vault with good frontmatter, tags, and summary."
4. The file is processed via kimi-claw → organized note created in Obsidian → RAG index updated.

### Option 2: Fortress Dashboard (Visual / MCP buttons)
1. Rebuild if needed:
   ```bash
   cd /opt/reclaw/tools && bash rebuild-fortress-dashboard.sh
   ```
2. Open: http://localhost:8080 (or Tailscale IP:8080)
3. Hard refresh (Ctrl+Shift+R)
4. Walk into the **Knowledge Vault** chamber (archivist with lantern).
5. Use the glowing **MCP ingest button** or drag files into the chamber area.
6. Watch live progress (glowing lantern + WS events).

### Option 3: CLI (Best for batch/folder)
```bash
cd /opt/reclaw
PYTHONPATH=. python3 -m core.cli ingest --file /path/to/document.pdf --model kimi_claw

# Or entire folder
PYTHONPATH=. python3 -m core.cli ingest --folder /path/to/pdfs --model kimi_claw
```

## Reload / Sync After Upload
```bash
cd /opt/reclaw
PYTHONPATH=. python3 -m core.cell "Reload ritual"
```
This refreshes the RAG index, Fortress dashboard, and Obsidian links.

## Where Notes Land
- Default: `Knowledge Vault/` or `Ravenstack/` folder inside your configured Obsidian vault.
- Each note gets clean frontmatter: title, date, source, tags, summary, key points, action items.
- Bidirectional links and good organization for long-term agent use.

## Verification
After upload:
- Open the note in Obsidian → check frontmatter + quality of extraction.
- Search the same content on https://vb2sxll3shzgg.kimi.page
- Check the Knowledge Vault chamber in Fortress for the new entry.

## Troubleshooting
- Button not visible? Hard refresh + run `rebuild-fortress-dashboard.sh` + reload ritual.
- No output in vault? Check `openclaw doctor --fix` and gateway status.
- Want Google Drive support? Mention it and we'll wire a pull-from-Drive option.

## Backend Details
- Powered by kimi-claw model for smart distillation.
- Uses existing `core.knowledge` pipeline + pypdf2 for PDFs.
- All runs go through ReClaw security gates and session isolation.
- Output is production-grade Markdown ready for agents, rural data reports, content packages, and ClawHub cells.

This is now your central long-term memory for ReClaw 2.0 monetization work.
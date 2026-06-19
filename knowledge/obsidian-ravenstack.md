# Obsidian & Ravenstack Management

**How to maintain the knowledge fortress for human + multi-agent use.**

This file details the production workflow for ingesting new material and keeping Ravenstack clean/scalable.

## Vault Structure Recommendations
In your Obsidian vault (desktop PC + git-synced repo):
```
Obsidian-Vault/
├── Ravenstack/              # Symlink or copy of project/knowledge/  (or add as folder)
│   ├── knowledge_index.md   # Main MOC — start here
│   ├── principles.md
│   ├── agent-architecture.md
│   ├── income-streams.md
│   └── ...
├── Rural Data/              # Existing from ReClaw outputs
├── Content/
├── Marketplace/
├── Agents/                  # SOULs, room memories
├── Queries/                 # Dataview saved queries
└── MOCs/                    # Maps of Content linking everything
```

**Pro Tip**: In Obsidian settings, enable "Detect all file extensions" and use the git plugin for auto-sync with the ReClaw-2.0 repo. The `knowledge/` folder in repo is the single source of truth.

## Dataview Queries for Usability
Add these to a `Ravenstack Dashboard.md`:

```dataview
TABLE file.mtime as "Last Updated", "[[knowledge_index.md|Index]]" as Link
FROM "Ravenstack"
WHERE contains(file.name, "red-flags") OR contains(file.name, "principles")
SORT file.mtime DESC
```

```dataview
LIST FROM "Ravenstack"
WHERE contains(text, "Etsy") OR contains(text, "Marketplace")
```

## Full Ingestion & Maintenance Workflow
**When user shares a new PDF, book excerpt, research, or file:**

1. **Receive Material**: PDF, scanned book pages, website export, or text. (Use skills like docx/pptx/xlsx if applicable.)
2. **Analyze for Value** (Human or OpenClaw/ReClaw agent with `read_file`, web_search, or LLM synthesis):
   - What high-value, non-obvious insights apply to ReClaw goals?
   - Relevant to which domains? (fraud, income, rural data, automation, content, grants, marketplace, SEO, compliance)
   - Extract **only** principles, frameworks, red flags, tactics, decision trees, examples.
   - **Strict Rule**: No >200 words of near-verbatim text from source. Synthesize in ReClaw voice. Attribute source at bottom.
3. **Map to File**:
   - Use `knowledge_index.md` to choose or create new topic file (kebab-case).
   - Append under appropriate heading using `KnowledgeManager.update_topic("topic", distilled_dict, section="Red Flags")`.
   - Or manually edit with Obsidian for complex merges.
4. **Format Strictly** per [[agent-architecture.md#file-format-standard]].
5. **Update Index**: Add bullet with short description and cross-links.
6. **Test Consumption**: 
   ```bash
   python3 -m core.knowledge  # or test script
   km = get_knowledge_manager()
   flags = km.get_section("fraud-examination", "red-flags")
   print(flags.content)
   ```
7. **Commit & Sync**:
   ```bash
   git add knowledge/
   git commit -m "ravenstack: distill [source] into [topic] — [key insight]"
   git push
   ```
   Desktop Obsidian will pick up via git pull or vault refresh. Sessions log knowledge references.

8. **Audit**: Review for bloat quarterly. Merge duplicate patterns. Prune outdated tactics.

## Long-Term Scalability
- **As Empire Grows**: Add files for new income streams (e.g. `youtube-faceless.md`, `etsy-automation.md`, `compliance-audits.md`). Create subfolders only after 10+ related files.
- **Agent Specialization**: marketplace_flips agent defaults to loading `marketplace-automation.md + fraud-examination.md + principles.md`.
- **RAG Integration Path**: Add `data/vectors/` with embeddings of each section. New `KnowledgeRetriever` class using local embeddings (sentence-transformers) for semantic "find similar tactics".
- **24/7 Durability**: Knowledge files are read-only in most sessions (low risk capability). Updates go through approval gate if high-impact.
- **Human Usability**: Use Obsidian plugins: Dataview, Tasks, Calendar, Kanban for empire ops; Excalidraw for decision trees; Advanced URI for agent links.

## Red Flags in Knowledge Management
- Storing raw PDFs in vault → bloat, copyright risk. *Action*: Extract → delete raw or archive offline.
- Inconsistent formatting → hard for agents to parse. *Fix*: Enforce template.
- Forgetting to update index → knowledge gets lost. *Fix*: `KnowledgeManager.update_topic()` does it.
- Over-reliance on one file → context bloat. *Fix*: Modular sections + targeted `get_section()`.

**This completes the Ravenstack architecture.** It makes the multi-agent system (content studio, marketplace flips, grant watcher, rural analyst, etc.) lean, knowledgeable, and persistent. Knowledge will not "disappear again."

**Last Updated:** 2026-06-19  
**Sources:** User query on durable knowledge for ReClaw empire, existing SOUL/ARCHITECTURE, Obsidian best practices.

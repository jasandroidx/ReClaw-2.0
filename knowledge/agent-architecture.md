# Agent Architecture & Ravenstack Usage

**How ReClaw multi-agents interact with the Ravenstack knowledge base.**

This file defines production-grade patterns for lean agents that scale to 24/7 operation across content creation, marketplace flips, rural analysis, grants, etc.

## Core Design Principles (from [[principles.md]])
- Agents remain small: <2000 token context per invocation where possible.
- Knowledge is **referenced**, not embedded by default.
- Durable via files in `knowledge/` (git-backed, Obsidian-linked).
- Future: RAG/vector embeddings over these distilled MD files for semantic search.

## Folder Structure (Ravenstack)
```
knowledge/
├── knowledge_index.md          # MOC + list of all topics with descriptions
├── principles.md
├── rural-government-analysis.md
├── fraud-examination.md
├── income-streams.md
├── marketplace-automation.md
├── content-creation.md
├── automation-patterns.md
├── obsidian-ravenstack.md
├── grant-watching.md
├── seo-outreach.md
├── compliance-risk.md
├── ... (new domains as empire grows)
└── _templates/                 # (optional) template.md for new topics
```

**Naming Convention**: `kebab-case-topic.md` (lowercase, hyphens, descriptive). Group related under subdirs only if >20 files in category (e.g. `knowledge/marketplace/ebay.md`).

## File Format Standard (Production Grade)
Every knowledge file MUST follow this template:

```markdown
# Topic-Name

**One-line purpose.** Last Updated: YYYY-MM-DD. Relevant to: [list domains].

## Principles
- Bullet 1
- Bullet 2

## Frameworks & Decision Trees
### Decision Tree Name
1. Step...
   - Condition → Action
   - Red Flag → Escalate

## Tactics & Patterns
- **Tactic**: Description. *ReClaw Example*: How applied to Etsy flip or rural lead gen.
- Use tables for comparisons (e.g. pricing strategies).

## Red Flags
- **[CRITICAL] Category**: Description + evidence pattern + recommended action.

## ReClaw Applications & Examples
- Specific to income streams, agent handoffs, 24/7 ops.

## Sources & Provenance
- Distilled from [Book/PDF name], [date], key pages synthesized.
- Operational experience from [session ID].

**Cross-References**: [[related-file#section]]
```

Use Obsidian callouts for emphasis:
> [!warning] High Risk
> Description...

> [!tip] Agent Action
> Load this section via KnowledgeManager.load_section("file", "tactics")

## Agent Interaction Model
1. **Default**: No knowledge pre-loaded. Agent decides what it needs based on task.
2. **Reference Pattern** (preferred):
   - Use `KnowledgeManager` (to be implemented in `core/knowledge.py`):
     ```python
     from core.knowledge import KnowledgeManager
     km = KnowledgeManager()
     principles = km.get("principles")  # returns parsed dict or markdown sections
     fraud_flags = km.get_section("fraud-examination", "red-flags")
     ```
   - Or direct file read via tools in OpenClaw session: `read_file("knowledge/fraud-examination.md")` then parse relevant headings.
3. **For Complex Tasks**: Orchestrator loads 2-3 relevant files, embeds summaries in handoff JSON.
4. **Ingestion Agent**: Dedicated "raven" or use openclaw agent to process new PDFs:
   - Extract high-value only.
   - Append to correct file under headings (use search_replace-like logic or append with date).
   - Never duplicate; merge similar concepts.
   - Update knowledge_index.md automatically.

## Future RAG / Vector Capabilities
- Embed each section using sentence-transformers or local model.
- Store in vector DB (Chroma/Qdrant in `data/vectors/`).
- Agents query: "find tactics for marketplace fraud detection" → top-k relevant snippets.
- Keep source MD files as ground truth.

## Integration Points in ReClaw 2.0
- Update `core/config.py` to expose `knowledge_path`.
- Add to `core/session.py`: auto-load relevant knowledge summaries into session context.
- Update SOUL.md files to reference specific sections (e.g. "Always cross-reference [[fraud-examination#red-flags]] before marketplace actions").
- In `agents/marketplace_flips/SOUL.md` (create if missing): "Load marketplace-automation.md + principles.md for every flip decision."
- Obsidian: Use Dataview to query all files with `red-flags` tag or specific frontmatter.

## Maintenance Workflow
See [[obsidian-ravenstack.md]] for full ingestion process.

This architecture ensures:
- Knowledge survives thread/agent restarts (file-based).
- No bloat in any single agent's context.
- Easy human browsing in Obsidian (graph view connects principles → income-streams → specific tactics).
- Scalable to dozens of specialized agents running 24/7.

**Last Updated:** 2026-06-19
**Applies to:** All agents (researcher, analyst, marketplace_flips, content_studio, grant_watcher, clawsmith, orchestrator, future ones).
```

**Cross-References**: [[principles.md]], [[obsidian-ravenstack.md]], [[income-streams.md]]

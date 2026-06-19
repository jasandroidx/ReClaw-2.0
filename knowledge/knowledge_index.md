# Ravenstack Knowledge Base

**The Digital Fortress** — Centralized, distilled knowledge for all ReClaw agents and the human operator.

This is the durable core of the ReClaw multi-agent money-generating empire. All high-value, actionable intelligence from books, PDFs, research, experiments, and operational experience is distilled here. No raw dumps — only principles, frameworks, tactics, red flags, decision trees, and patterns that agents can directly apply.

**Core Rules for this Knowledge Base:**
- **Distilled Only**: Extract and synthesize. Never include large blocks of copyrighted raw text. Summarize in your own words with clear attribution where critical.
- **Actionable**: Every section must include "How ReClaw Applies This", decision criteria, or concrete examples tied to income streams (Etsy, eBay, Facebook Marketplace flips, Shopify, content creation, rural data services, grants, etc.), fraud prevention, or agent operations.
- **Structured**: Use consistent headings, bullets, tables, callouts for quick agent consumption and Obsidian graph/querying.
- **Modular**: One primary topic per file. Link between files using Obsidian `[[wikilinks]]`.
- **Versioned & Audited**: Update with date and source. Commit to Git after changes. Agents log which knowledge files they referenced in session memory.
- **Scalable**: As new domains (e.g. SEO automation, YouTube scripting, compliance auditing) are added, create new `.md` files following the naming convention.

## Knowledge Files Index

### Foundational
- [[principles.md|Principles & Philosophy]] — Core non-negotiables, truth-seeking, execution mindset, security, least-privilege, cashflow-first rules that govern all agents and decisions.
- [[agent-architecture.md|Agent Architecture & Ravenstack Usage]] — How agents interact with this knowledge base (KnowledgeManager patterns), reference methods, RAG future-proofing, SOUL integration, file format standards.
- [[obsidian-ravenstack.md|Obsidian & Ravenstack Management]] — Vault integration, Dataview queries, full ingestion workflow for PDFs/books, maintenance, graph navigation for human usability.

### Core Domains
- [[rural-government-analysis.md|Rural Government Data Analysis]] — Red flags, data sources, budget analysis patterns, property record heuristics, compliance signals for county-level insights and lead generation. (Distilled from current ReClaw rural_data module + future PDFs.)
- [[fraud-examination.md|Fraud Examination & Detection]] — Red flags, investigation frameworks, document analysis techniques, behavioral indicators applicable to marketplace sellers, grant applications, and rural data.
- [[income-streams.md|Income Streams & Business Models]] — Frameworks for multiple revenue channels: Etsy/Shopify print-on-demand, eBay/Facebook Marketplace arbitrage/flips, faceless content (YouTube/TikTok), service-based (rural data reports, compliance audits, grant writing), SaaS dashboard.
- [[marketplace-automation.md|Marketplace Automation & Flips]] — Tactics for Facebook Marketplace, eBay, Etsy automation; sourcing, pricing, listing optimization, risk mitigation, scaling with agents.
- [[content-creation.md|Content Creation Systems]] — Faceless channel production pipelines, script frameworks, thumbnail/SEO strategies, repurposing rural data insights into monetizable videos, thumbnails, newsletters.

### Operational
- [[automation-patterns.md|Automation & Agent Patterns]] — Reusable workflows, multi-agent orchestration, handoff protocols, quality gates, error recovery, monitoring for 24/7 operation.
- [[obsidian-ravenstack.md|Obsidian & Knowledge Management]] — Vault structure, Dataview queries, MOC patterns, ingestion workflow, graph maintenance for human + agent usability.

### Specialized (expand as needed)
- [[grant-watching.md|Grant & Funding Intelligence]] — Sources, eligibility frameworks, application red flags, automation opportunities.
- [[seo-outreach.md|SEO & Outreach Forge]] — Link building, audit patterns, cold outreach templates aligned with ReClaw services.
- [[compliance-risk.md|Compliance & Risk Management]] — Background check friendly practices, legal boundaries for data scraping/analysis, marketplace seller compliance.

**Last Updated:** 2026-06-19  
**Total Files:** 5 (expand as new PDFs/books ingested)  
**Purpose:** Prevent context bloat. Agents load only the 1-3 most relevant files per task via the KnowledgeManager (`core/knowledge.py`). Human uses Obsidian links, embeds, Dataview for navigation. Knowledge survives all resets.

## Usage for Agents
See [[agent-architecture.md]] for exact patterns. Example:
```python
# In agent code or via tool
knowledge = KnowledgeManager()
principles = knowledge.load_topic("principles")
fraud = knowledge.load_section("fraud-examination", "red-flags")
```

## Ingestion Workflow
1. User shares PDF/book/file.
2. OpenClaw/ReClaw agent (or human) analyzes for high-value extractable insights relevant to ReClaw goals.
3. Distill into existing or new topic file under correct headings.
4. Update this index with description and links.
5. Commit to repo (`git add knowledge/ && git commit -m "knowledge: add/update [topic]"`).
6. Sync to Obsidian vault on desktop/PC if separate.

**Ravenstack ensures knowledge survives resets, scales with empire, keeps agents lean.**

---

*Part of ReClaw 2.0 — https://github.com/jasandroidx/ReClaw-2.0. All changes audited via sessions.*

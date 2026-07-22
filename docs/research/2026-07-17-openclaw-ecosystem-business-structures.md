# OpenClaw Ecosystem: Agent Structures, Skills Marketplaces & Business Use Cases

**Date:** 2026-07-17  
**Scope:** OpenClaw (ex-Clawdbot / Moltbot), ClawHub, Hermes Agent, community multi-agent patterns, documented production/revenue use cases, competitor playbooks  
**Method:** Official docs, GitHub API, Droptica case roundup, founder write-ups, security reports, X/web secondary sources  
**Caveats:** Star counts and social ROI claims move fast. Business numbers below are **as reported by named operators or secondary journalism**, not independently audited. Security “malicious skill” counts vary by auditor and date. Firecrawl returned **HTTP 402** this session — scraping fell back to web_search / open_page / web_fetch / GitHub API.

---

## 1. What OpenClaw is (short)

OpenClaw is a **self-hosted personal AI agent / gateway** that:

- Runs on your machine or VPS (often Docker)
- Connects to chat surfaces (WhatsApp, Telegram, Discord, Slack, iMessage, Signal, etc.)
- Gives the model tools (shell, browser/CDP, files, sessions, cron, plugins)
- Uses a **markdown workspace** as identity + operating memory (`SOUL.md`, `AGENTS.md`, skills, daily notes)
- Extends via **skills** (`SKILL.md` packs) and a public registry (**ClawHub**)

**Official anchors**

| Resource | URL |
|----------|-----|
| Site | https://openclaw.ai/ |
| Docs | https://docs.openclaw.ai/ |
| Main repo | https://github.com/openclaw/openclaw |
| ClawHub site | https://clawhub.ai |
| ClawHub docs | https://docs.openclaw.ai/clawhub |
| ClawHub repo | https://github.com/openclaw/clawhub |
| Skills docs | https://docs.openclaw.ai/tools/skills |
| Multi-agent docs | https://docs.openclaw.ai/concepts/multi-agent |
| Workspace docs | https://docs.openclaw.ai/concepts/agent-workspace |
| SOUL guide | https://docs.openclaw.ai/concepts/soul |

**Live GitHub snapshot (this session, 2026-07-17 via API)**

| Repo | Stars | Notes |
|------|------:|-------|
| [openclaw/openclaw](https://github.com/openclaw/openclaw) | **383,201** | TypeScript; created 2025-11-24; “lobster way” |
| [openclaw/clawhub](https://github.com/openclaw/clawhub) | **9,166** | Skill + plugin registry |
| [openclaw/agent-skills](https://github.com/openclaw/agent-skills) | **935** | Canonical shared coding-agent skills |
| [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | **216,131** | Closest “local agent” rival |

Creator: **Peter Steinberger** (ex-PSPDFKit). Project lineage: **Clawd → Clawdbot → Moltbot → OpenClaw**. Steinberger later joined OpenAI while stewarding OpenClaw as open/independent ([GitHub profile narrative](https://github.com/steipete); Lex Fridman coverage). Secondary press claims “fastest star climb in GitHub history” and ~250k stars in ~60 days — **treat growth superlatives as marketing/secondary**, even though absolute star counts are verifiable via API.

**Legacy paths still matter for migrations:** `~/.clawdbot/`, `~/.moltbot/`, configs `clawdbot.json` / `moltbot.json` (see Hermes migrate guide).

---

## 2. How the community structures agents & monorepos

### 2.1 Runtime topology (official)

```
Chat channels (WA / TG / Discord / …)
        │
        ▼
┌───────────────────────────┐
│  OpenClaw Gateway process │  ← one control plane (recommended)
│  openclaw.json            │
│  bindings → agentId       │
└───────────┬───────────────┘
            │
   ┌────────┼────────┐
   ▼        ▼        ▼
 agent A   agent B  agent C
 workspace  workspace workspace
 SOUL.md    SOUL.md   SOUL.md
 AGENTS.md  AGENTS.md AGENTS.md
 skills/    skills/   skills/
 agentDir   agentDir  agentDir
 sessions   sessions  sessions
```

Docs: [Multi-agent routing](https://docs.openclaw.ai/concepts/multi-agent).

**One agent = full persona scope:**

| Layer | Location (defaults) | Purpose |
|-------|---------------------|---------|
| Workspace | `~/.openclaw/workspace` or `workspace-<agentId>` | Files, bootstrap MD, local skills, memory notes |
| State / agentDir | `~/.openclaw/agents/<id>/agent` | Auth profiles, model registry, SQLite sessions |
| Config | `~/.openclaw/openclaw.json` | Agents list, channels, bindings, skills policy |
| Managed skills | `~/.openclaw/skills` | Shared across local agents |
| Credentials | `~/.openclaw/credentials/` | Channel/provider secrets (**not** in workspace git) |

CLI: `openclaw agents add|list|bindings|bind`, `openclaw skills install|update|verify`, `openclaw gateway restart`, `openclaw doctor`.

**Hard community rule (also on ReClaw host):** one gateway process. Multiple gateways fight over sessions/channels/config.

### 2.2 Workspace file conventions (official + community)

From [Agent workspace](https://docs.openclaw.ai/concepts/agent-workspace) and community write-ups:

| File | Role | Load pattern |
|------|------|----------------|
| **SOUL.md** | Voice, stance, hard boundaries | Every session — **keep lean** |
| **AGENTS.md** | Operating rules, task playbooks, tool policy | Every session |
| **USER.md** | Who the human is / how to address them | Every session |
| **IDENTITY.md** | Name, vibe, emoji | Bootstrap / identity UI |
| **TOOLS.md** | Local tool conventions (guidance only) | Reference |
| **HEARTBEAT.md** | Short checklist for heartbeat runs | Cron/heartbeat |
| **BOOT.md** / **BOOTSTRAP.md** | Startup / first-run ritual | On restart / once |
| **MEMORY.md** | Curated long-term facts | Main private session |
| **memory/YYYY-MM-DD.md** | Daily logs | On demand / session start |
| **skills/\*\*/SKILL.md** | Highest-precedence skills for that agent | Session skill snapshot |

**Community consensus (Capodieci / OpenAgents.mom — blog, not official):**

- **SOUL.md = who** (tone + 4–6 hard “never” lines; target ~150–300 words)
- **AGENTS.md = how** (task blocks: deploy, email, review…)
- Bloated SOUL.md (>~1,200 words) is blamed for “dumb zone” context overload  
  Source: https://capodieci.medium.com/ai-agents-034-why-your-soul-md-is-making-your-agent-dumber-and-how-to-fix-it-b0824be2966a  
  Official SOUL guide: https://docs.openclaw.ai/concepts/soul

**Git practice:** private workspace repo with bootstrap files + `memory/`; **never** commit `~/.openclaw/openclaw.json`, auth-profiles, or channel tokens.

### 2.3 Multi-agent patterns in the wild

| Pattern | How it works | Evidence |
|---------|--------------|----------|
| **One gateway, N agents** | `agents.list[]` + channel `bindings` | Official multi-agent docs |
| **Channel split** | WhatsApp → “chat” agent; Telegram → “deep work” | Official examples |
| **Role agents** | Sales / DevBot / PR / CFO each with workspace + skills | Travel Code DEV post |
| **Coordinator + workers** | “Lobster” daily standup + routing | Travel Code + Droptica |
| **Sandbox tiers** | Main host-full; family/public sandboxed + tool deny | https://docs.openclaw.ai/tools/multi-agent-sandbox-tools |
| **Sub-agents / sessions** | `sessions_spawn`, agent-to-agent (off by default) | Official tools docs |
| **Mac Mini node hosts** | Residential browser/IP via Tailscale node | Travel Code architecture |
| **Community kits** | Ready multi-agent packs | e.g. https://github.com/shenhao-stu/openclaw-agents |
| **Dev pipelines** | programmer / reviewer / tester workspaces + workflow engine | https://dev.to/ggondim/how-i-built-a-deterministic-multi-agent-dev-pipeline-inside-openclaw-and-contributed-a-missing-4ool |

**Travel Code production shape (founder primary source):**

- 1 Linux VPS (4 vCPU / 16 GB), **one gateway**, 12 agents, 48 staggered crons  
- Per-agent Telegram group as UI  
- Local **Ollama** for cheap heartbeats; Claude for real work  
- Skills from ClawHub + custom; LanceDB vector memory  
- Agent-to-agent: DMs + task queue + heartbeat async  
  Source: https://dev.to/egorceo/i-run-a-travel-saas-with-12-ai-agents-and-48-cron-jobs-on-openclaw-heres-my-exact-setup-264h

**TelexPH shape (Droptica secondary):** one OpenClaw instance, **5 specialized agents**, Discord gateway, GoHighLevel tools, 15 skills (5 ClawHub + 10 custom), 7 crons, Docker package — often installed by **external agency** (LaunchMyOpenClaw mentioned).  
  Source: https://www.droptica.ai/blog/ai-agent-in-company-5-examples/

### 2.4 “Monorepo” vs split state (what people actually version)

OpenClaw is **not** a monorepo product layout for end users. Community structure tends to be:

```
# Host state (not one public monorepo)
~/.openclaw/
  openclaw.json          # agents, bindings, channels, skills policy
  skills/                # managed / --global installs
  agents/<id>/agent/     # auth + sqlite (do not publish)
  credentials/

# Versioned workspace(s) — often private git
workspace-main/          # or agents.list[].workspace paths
  SOUL.md AGENTS.md USER.md MEMORY.md
  skills/
  memory/
workspace-sales/
workspace-dev/
...

# Optional product monorepos (companies)
gtm-os/  seo-os/  microservices built BY agents (Travel Code pattern)
```

**ReClaw note:** ReClaw is a **domain pipeline monorepo** (`agents/`, `core/`, vault SOT) sitting **beside** OpenClaw gateway — a common hybrid: OpenClaw as always-on operator shell; Python/API monorepo as deterministic product logic.

### 2.5 Skills architecture (official)

Skills = directory + `SKILL.md` (AgentSkills / https://agentskills.io format) with YAML frontmatter + instructions. Optional scripts/templates next to the skill.

**Load precedence (high → low):**

1. `<workspace>/skills`
2. `<workspace>/.agents/skills`
3. `~/.agents/skills`
4. `~/.openclaw/skills` (managed)
5. Bundled
6. `skills.load.extraDirs` + plugin skills

**Visibility vs location:** per-agent `agents.list[].skills` allowlist **replaces** defaults (does not merge).  
**Security:** treat third-party skills as untrusted; `openclaw skills verify`; sandbox + install policy.  
**Skill Workshop:** agent proposes skill revisions → human apply.  
Docs: https://docs.openclaw.ai/tools/skills · https://openclaw.ai/blog/openclaw-agent-skill-workshop

---

## 3. ClawHub & the skills marketplace

### 3.1 What ClawHub is

- Public registry for **skills** (versioned `SKILL.md` bundles) and **plugins** (code/bundle packages)
- Site: https://clawhub.ai  
- Install: `openclaw skills search|install|update`  
- Publish/auth: separate `clawhub` CLI (`npm i -g clawhub`)  
- Docs: https://docs.openclaw.ai/clawhub  
- Repo: https://github.com/openclaw/clawhub  

Features commonly cited: semver, tags, changelogs, vector/semantic search, stars/downloads, security scan summaries on detail pages, GitHub-age gate for publish.

### 3.2 Scale (secondary sources — numbers disagree by date)

| Claim | Source class | URL |
|-------|--------------|-----|
| ClawHub as official skill registry | Official docs | https://docs.openclaw.ai/clawhub |
| “Thousands” of community skills; npm-for-agents framing | DataCamp guide | https://www.datacamp.com/blog/best-clawhub-skills |
| VoltAgent curated **5,300–5,400+** skills | GitHub awesome list | https://github.com/VoltAgent/awesome-openclaw-skills |
| Blog claims of **13k+** skills in registry | Secondary blogs (e.g. AI Skill Market, Skywork) | https://aiskill.market/blog/openclaw-skill-ecosystem-explained |
| GitHub topic `openclaw-skills` ~690 public repos | GitHub topics | https://github.com/topics/openclaw-skills |

**Do not treat any single “total skills” number as ground truth** without a ClawHub API snapshot from the same day.

### 3.3 Security history (critical for business deployers)

| Issue | Summary | Sources |
|-------|---------|---------|
| **ClawHavoc / malicious skills** | Hundreds–1,000+ skills flagged over time (installer social eng, reverse shells, credential theft). Counts: 341 → 820+ → 1,184 depending on auditor/date | Reddit cybersec; https://blog.cyberdesserts.com/openclaw-malicious-skills-security/ ; ClawTrust; arXiv scanner-disagreement paper https://arxiv.org/html/2606.01494v1 |
| **Ranking manipulation** | Silverfort: vulnerability to game rankings to #1 skill | https://www.silverfort.com/blog/clawhub-vulnerability-enables-attackers-to-manipulate-rankings-to-become-the-number-one-skill/ |
| **Unit 42 (Palo Alto)** | Five malicious skills with infostealers bypassed checks; removed | https://www.darkreading.com/cyber-risk/malicious-openclaw-skills-clawhub-threaten-ai-supply-chain |
| **CVE-2026-25253** | Frequently cited one-click RCE / WebSocket class issue (CVSS ~8.8 in secondary writeups); patched in early 2026 releases | ClawTrust / security blogs |
| **Snyk-style audits** | High % of skills with security flaws; subset critical/credentials-in-context | Secondary essays e.g. https://www.dimolarov.com/essays/openclaw-skills-credential-security |

**Operational implication:** production installs should use allowlists, sandbox non-main agents, verify scans, prefer private skill forks, and avoid “install top ClawHub skill unreviewed.”

### 3.4 Adjacent skill discovery

- VoltAgent awesome list (curated filter of registry)  
- Official `openclaw/agent-skills` for **coding-on-OpenClaw** workflows  
- AgentSkills format portability (Claude Code / Codex / Goose discussions)  
- “SkillClaw”, skills.sh, etc. — third-party indexes; quality varies  

---

## 4. Hermes Agent (closest related stack)

| | OpenClaw | Hermes Agent |
|--|----------|--------------|
| Org | openclaw | Nous Research |
| Stars (this session) | ~383k | ~216k |
| Core metaphor | Gateway control plane + workspace files | Agent loop + self-improvement |
| Identity | Per-**workspace** `SOUL.md` | Per-**instance** `~/.hermes/SOUL.md` |
| Skills | Mostly human-authored + ClawHub | Human + **auto skill_manage** from successful workflows |
| Memory | Markdown SOT + hybrid search | Small always-on MEMORY/USER + SQLite FTS sessions + optional Honcho |
| Multi-agent | First-class `agents.list` + bindings | Profiles / Kanban multi-agent (evolving) |
| Migration | — | `hermes claw migrate` from `~/.openclaw` (also legacy moltbot/clawdbot) |

Sources:

- Compare essay: https://www.turingpost.com/p/hermes  
- Migrate guide: https://hermes-agent.nousresearch.com/docs/guides/migrate-from-openclaw  
- Hermes GitHub: https://github.com/NousResearch/hermes-agent  
- Community: “OpenClaw vs Hermes” YouTube/explainers (secondary)

**Business takeaway:** OpenClaw wins for **channel-native multi-persona ops** and inspectable workspace git. Hermes wins for **safer-default self-improving loop** and cleaner cron worker narrative (per Turing Post framing). Some operators run **both** or host both via managed platforms (e.g. MyClaw claims — **unverified product marketing** on X).

---

## 5. Documented business / production use cases

### 5.1 Droptica five-deployment roundup (primary secondary synthesis)

**Article:** [AI Agent in a Company: 5 Real-World OpenClaw Deployments](https://www.droptica.ai/blog/ai-agent-in-company-5-examples/) (Grzegorz Bartman, 2026-04-18)  
**Services page:** https://www.droptica.ai/services/openclaw/

Droptica states they filtered for named companies, concrete numbers, ≥3 months production. **Still secondary reporting** unless the company also published first-party posts.

#### Travel Code (New York — corporate travel SaaS)

| Metric | Reported |
|--------|----------|
| Headcount | 23 people |
| Agents | 12 OpenClaw agents |
| Cron | 48 jobs/day |
| Coordinator | “Lobster” standup 04:00 UTC |
| GMV / scale | ~$9M GMV, 100k+ travelers/year (Droptica) |
| Hire avoidance | ~$400k/year (5 planned hires not made) |
| Agent cost | ~$350–400/mo (VPS $48, Browserbase ~$50, Claude Max $200, Ollama) |
| Feature velocity | 2–3 → 6–8 features/month |
| Founder oversight | ~30 min/day |

Notable agents: Sales (competitor review scraping → 73 hot / 255 warm leads), DevBot (35 skills; writes endpoints), PR (HARO/Qwoted → Kiplinger’s), Analyst (weekly competitor deep dives).

**First-party corroboration:** Egor Karpovich DEV post (12 agents, 48 crons, architecture, costs table) — https://dev.to/egorceo/i-run-a-travel-saas-with-12-ai-agents-and-48-cron-jobs-on-openclaw-heres-my-exact-setup-264h  
Product: https://travel-code.com  

**Label:** Company-reported ROI; not third-party audited.

#### AgencyBoxx / Meticulosity (Vancouver HubSpot agency)

| Metric | Reported (Droptica) |
|--------|---------------------|
| Team | 10 people, 62 clients; agency 17 years, 75+ clients |
| Agents | 8 |
| Hours reclaimed | **32 h/week** |
| Cost | ~$3–4/day tokens (~$90–120/mo) + local Mac/GPU |
| Annual savings claim | $183–319k; ROI 125–290× |
| Productization | AgencyBoxx productized from internal stack (>50k LOC) |

Agents: Email triage (700+ email actions/day; morning triage 65→10 min), SLA monitor (60s), time tracking (**pure Python, $0 AI**), prospecting (7,300 enriched leads).  
**Lesson:** model tiering — 80% cheap/local, 20% premium after burning $50/2h on GPT-4 everything.

#### JustPaid (YC W23 FinOps)

| Metric | Reported |
|--------|----------|
| Team | 9 people, 4 engineers |
| Agents | 7-agent “autonomous eng team” |
| Architecture | OpenClaw “Gilfoyle” (Bedrock orchestration) + **Claude Code** as hands |
| Cost evolution | $4k/week → $10–15k/mo → ~$5.3k/mo after Max flat-fee coding |
| Output | 10 major features in a month ≈ “10 eng-months” (CTO estimate) |
| Cultural anecdote | New hire onboarded by agent via Slack |

Press: [WSJ](https://www.wsj.com/tech/ai/meet-the-startup-that-used-ai-and-openclaw-to-automate-its-own-developers-9e733351) (paywall); Droptica summary; AI2ROI case study https://ai2roi.substack.com/p/ai-to-roi-case-study-justpaid-plays  

**Note:** JustPaid’s own blog also discusses OpenClaw in a **finance/trust** essay angle — different content from the eng-team case: https://www.justpaid.ai/blog/openclaw-role-next-financial-era  

#### TelexPH (Philippines BPO, 300+ employees)

| Metric | Reported |
|--------|----------|
| Scale | 300+ staff, 2,000+ concurrent clients |
| System | “Aria” — **1 OpenClaw instance, 5 agents** |
| Stack | Docker (466-file package), GHL V2 (30 tools), 15 skills, 7 crons, Discord |
| Installer | External agency (LaunchMyOpenClaw) — no in-house AI team required |
| Wins | CRM workflows 30–60 min → <30s; stale lead scan every 4h; NL pipeline moves; docs for 300 staff |

#### HOAgent (HOA community assistant)

| Metric | Reported |
|--------|----------|
| Pattern | RAG + MCP over CC&Rs/bylaws + local law |
| Outcome | **65% fewer** staff questions; 3× faster replies; ~1 FTE savings |
| **OpenClaw proof** | Droptica **explicitly says Galang AI did not disclose** OpenClaw under the hood — **pattern-adjacent only** |

### 5.2 Other named business / revenue narratives

| Case | Claim | Source class | URL |
|------|-------|--------------|-----|
| Nat Eliason “Felix” bot | $1,000 → **$14,718** in ~3 weeks (site, info product, X) | YouTube tutorial / creator claim | https://www.youtube.com/watch?v=nSBKCZQkmYw — **unverified social/creator revenue** |
| Greg Isenberg vertical agency playbook | Productize boring vertical workflows → Upwork proof → package → enterprise SLA | X + podcast framing | https://x.com/gregisenberg/status/2024247983999521123 — **strategy, not audited P&L** |
| VibeMarketer setup guides | Founders running business 24/7 including Contra hires | X lead-magnet | https://x.com/VibeMarketer_/status/2024217734771265712 — **unverified** |
| Jesse Genet (How I AI / Lenny) | 5 agents on Mac Minis for home/finance/code | Newsletter summary | https://www.lennysnewsletter.com/p/this-week-on-how-i-ai-5-openclaw |
| Sphere “100 use cases” | Agency claims 60+ workflows advised | Marketing blog | https://www.sphereinc.com/blogs/100-openclaw-use-cases-you-can-try-today |
| Tencent Cloud case pack | CS response 45 min → 8s etc. | Cloud marketing | https://www.tencentcloud.com/techpedia/141568 — **anonymized / marketing** |

### 5.3 Selling OpenClaw setups (business-of-the-tool)

Clear commercial layer has formed **around** the OSS:

| Offer type | Price signals (marketing sites) | Examples |
|------------|----------------------------------|----------|
| Setup services | $299–$1,999 claimed market rates | https://launchmyopenclaw.com/ |
| Agency retainers | $500–$2k/mo + $2k–$10k setup (guide claims) | https://launchmyopenclaw.com/ai-automation-agency-guide |
| Managed / white-label hosting | From ~$4/mo hosting claims; white-label reseller programs | Agent 37 blog https://www.agent37.com/blog/white-label-openclaw-build-an-ai-agent-offer-without-building-a-cloud ; MyClaw X ads |
| Enterprise deploy consulting | Droptica OpenClaw for Business | https://www.droptica.ai/services/openclaw/ |
| One-click VPS templates | Contabo, Dokploy, Hostinger, Tencent Lighthouse, Northflank | Various host blogs |
| Course/YouTube funnels | “Build & sell AI agents” | Multiple YouTube titles — quality varies |

**ReClaw relevance:** selling “vertical agent workspaces + skills + ops retainers” is the dominant **go-to-market** pattern in the ecosystem — not selling the gateway itself.

---

## 6. Architectural lessons that recur in successful deploys

From Travel Code + AgencyBoxx + JustPaid + TelexPH + official docs:

1. **One gateway, many agents** (not many gateways)  
2. **Role-scoped SOUL/AGENTS + skill allowlists**  
3. **Staggered crons / heartbeats** (avoid thundering herd OOM)  
4. **Model tiering** — local/small for wakeups; premium for real work; flat-fee coding harnesses when possible  
5. **Deterministic code under the agent** — agents orchestrate; Python/APIs do heavy lifting (Isenberg playbook; Travel Code GTM-OS)  
6. **Human approval on external write/send**  
7. **Telegram/Discord as ops UI** for non-technical staff  
8. **Cost architecture is a feature** (JustPaid burn story)  
9. **Self-learning crons** updating knowledge files (Travel Code weekly digests)  
10. **Security**: private skills, sandbox public agents, never trust ClawHub top charts

**What failed (Droptica synthesis):** simultaneous wake storms; routing everything to top models; rate-limit cascade; browser/Cloudflare friction; relationship work still human; Reddit blocks server IPs.

---

## 7. Competitor frameworks with clearer business playbooks

OpenClaw’s playbook is **“digital employees on chat + tools.”** Python/enterprise frameworks have clearer **app-embedding** stories:

| Framework | Business fit | Playbook clarity |
|-----------|--------------|------------------|
| **LangGraph** | Stateful production workflows, audit trails, enterprise Python | High — graph/state = compliance-friendly |
| **CrewAI** | Role crews for marketing/research/ops demos → products | High DX; many agency templates |
| **AutoGen / MS Agent stack** | Multi-agent conversation, Microsoft enterprise | High for MS shops |
| **OpenAI Agents SDK / Anthropic tooling** | Managed platform agents | Highest commercial packaging |
| **n8n / Zapier + LLM** | Low-code ops automation | Clearest SMB monetization historically |
| **Hermes** | Self-improving local worker | Growing; fewer named $ case studies than OpenClaw yet |
| **Dify / Mastra** | Visual / TS agent apps | Productized SaaS builders |

Comparisons (secondary):  
https://openclawdirectory.co.uk/blog/openclaw-vs-crewai-vs-autogen-vs-langgraph/  
https://dev.to/dextralabs/top-10-agentic-ai-frameworks-compared-langgraph-vs-crewai-vs-autogen-vs-benchmarks-inside-1d6g  

**Gap for OpenClaw GTM:** exploding consumer/creator case studies; **fewer procurement-grade SLAs** than LangGraph-in-product or Microsoft stacks. Droptica/AgencyBoxx style **managed deploy** fills that gap commercially.

---

## 8. Implications for ReClaw / Ravenstack

| OpenClaw community pattern | ReClaw alignment |
|----------------------------|------------------|
| SOUL lean / AGENTS operational | Already separated (`SOUL.md`, `AGENTS.md`, vault ORACLE) |
| Per-room agents | Clawforge rooms + agent roster under `agents/` |
| Skills as SKILL.md + ClawHub | Local skills under OpenClaw workspace + Matt Pocock skills; treat ClawHub as **untrusted** |
| One gateway | Hard rule: Docker `openclaw-gateway` only |
| County/product monorepo beside gateway | ReClaw monorepo + MCP `:8100` + Obsidian SOT |
| Human gates | `pending_gates` / county queue approve-reject |
| Model tiering | Local Ollama primary; paid models sparingly |
| Vertical productization | Rural data / content / marketplace income streams = same “vertical workspace” GTM as Greg/Travel Code |

**Do not copy:** unvetted ClawHub bulk installs; multi-gateway; SOUL bloat; concurrent unstaggered agent wakes on small VPS.

---

## 9. Source index (selected)

### Official
- https://openclaw.ai/
- https://docs.openclaw.ai/
- https://docs.openclaw.ai/concepts/multi-agent
- https://docs.openclaw.ai/concepts/agent-workspace
- https://docs.openclaw.ai/concepts/soul
- https://docs.openclaw.ai/tools/skills
- https://docs.openclaw.ai/clawhub
- https://github.com/openclaw/openclaw
- https://github.com/openclaw/clawhub
- https://github.com/openclaw/agent-skills
- https://clawhub.ai

### Hermes / related
- https://github.com/NousResearch/hermes-agent
- https://hermes-agent.nousresearch.com/docs/guides/migrate-from-openclaw
- https://www.turingpost.com/p/hermes
- https://mager.co/blog/2026-04-28-hermes-agent-explainer/

### Production / business
- https://www.droptica.ai/blog/ai-agent-in-company-5-examples/
- https://www.droptica.ai/services/openclaw/
- https://dev.to/egorceo/i-run-a-travel-saas-with-12-ai-agents-and-48-cron-jobs-on-openclaw-heres-my-exact-setup-264h
- https://www.wsj.com/tech/ai/meet-the-startup-that-used-ai-and-openclaw-to-automate-its-own-developers-9e733351
- https://ai2roi.substack.com/p/ai-to-roi-case-study-justpaid-plays
- https://launchmyopenclaw.com/
- https://launchmyopenclaw.com/ai-automation-agency-guide

### Skills / security
- https://github.com/VoltAgent/awesome-openclaw-skills
- https://www.datacamp.com/blog/best-clawhub-skills
- https://www.silverfort.com/blog/clawhub-vulnerability-enables-attackers-to-manipulate-rankings-to-become-the-number-one-skill/
- https://www.darkreading.com/cyber-risk/malicious-openclaw-skills-clawhub-threaten-ai-supply-chain
- https://blog.cyberdesserts.com/openclaw-malicious-skills-security/
- https://arxiv.org/html/2606.01494v1

### Conventions / community
- https://capodieci.medium.com/ai-agents-034-why-your-soul-md-is-making-your-agent-dumber-and-how-to-fix-it-b0824be2966a
- https://github.com/shenhao-stu/openclaw-agents
- https://x.com/gregisenberg/status/2024247983999521123

---

## 10. Research gaps / follow-ups

1. **ClawHub live catalog size** — need authenticated registry API dump (Firecrawl 402 this session).  
2. **AgencyBoxx first-party metrics** — only via Droptica so far.  
3. **TelexPH Aria** — no public GitHub package confirmed here.  
4. **Product Hunt launch page** — not deeply archived in this pass.  
5. **Reddit** — summaries via search only; IP/blocks possible.  
6. **Independent audit** of Travel Code / JustPaid dollar claims.  
7. **OpenClaw Foundation governance** post-OpenAI hire for Steinberger.

---

*Compiled for ReClaw-2.0 operator research. Prefer primary URLs over this note when making deploy decisions.*

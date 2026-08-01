---
name: county-video-shorts
description: >
  Build viral Indiana-county YouTube Shorts / TikTok packages: surprising local
  history cold-open + verified public-money kicker, primary sources only, ready
  for faceless TTS render. Use when the user says county video, county shorts,
  interesting county facts, money kicker, review card package, viral county
  short, "I bet you didn't know" Indiana county, Form 100R + history package,
  or runs /county-video-shorts. Prefer this over silent-auditor flag-mills for
  shareable short-form content.
---

# County Video Shorts — Viral Indiana County Package

**One Indiana county → one shareable Short (70–90 sec) that can go viral.**

Two research tracks feed **one** script:

| Track | Job | Risk |
|-------|-----|------|
| **A — Interesting facts** | Pattern-break history / geography / “firsts” / famous residents | Low (celebratory) |
| **B — Public money** | Exact $ from Gateway 100R, SBOA finals, DLGF orders | Medium (fair-report only) |

**Product goal:** scroll-stopping hook → “wait what” retention → money punch → soft CTA.  
**Not the product:** 60-flag audit dumps, IsolationForest cold opens, estimator-site salaries, wrong-state counties.

Vault twin (narrative SOT): `obsidian_vault/Ravenstack/skills/county-video-package.md`  
Silent Auditor legal SOT (Track B language): `ReClaw-2.0/docs/SILENT-AUDITOR-WORKFLOW.md`

---

## 0) Mandatory first moves (every run)

1. **Load this skill fully** — do not freestyle a weaker version.
2. **Inventory tools** for 30–60s: which of the tool stack below is live *this session* (MCP, Firecrawl, Chrome, CLI). Use what works; fall back deliberately.
3. **Confirm Indiana** — county name + **FIPS** + **DLGF county #** before trusting any dollar or news hit.
4. **No seed-as-truth** for video claims unless the user asked for cache. Prefer **live primary URLs**. Local cache is discovery only, not citation.
5. **Deliver to outbox correctly** (see §7). File on disk alone is not delivery.

---

## 1) Tool / plugin / skill stack (USE THEM)

You get better results by **actually calling tools**, not recalling numbers. Prefer this order:

### Discovery & scrape
| Tool | Use for |
|------|---------|
| **Firecrawl** (`firecrawl search` / `scrape` / MCP firecrawl skills) | Find primary pages, scrape Census/IBC/news, discover DLGF PDF URLs |
| **Chrome DevTools MCP** (`navigate_page`, `fill`, `evaluate_script`, snapshot) | **Gateway Form 100R** interactive report (JS-heavy — plain scrape fails) |
| **web_search / web_fetch** | Quick discovery when Firecrawl is down |
| **pdftotpm + tesseract** or venv `pypdf`/`pymupdf` | DLGF budget orders, SBOA PDFs, scanned wage ordinances |

### Indiana public-money primaries
| Source | How |
|--------|-----|
| **Gateway 100R** | Browser: `gateway.ifionline.org` → Employee Compensation → Year → County → unit `{COUNTY} COUNTY` → View Report → extract named $ |
| **SBOA filings API** | `POST https://audit.sboa.in.gov:8090/filings/search` with `{"pageNumber":1,"pageSize":50,"counties":["{County}"],"unitTypes":["county","town","city"],"sortColumn":"reportDate","sortDescending":true}` (`verify=False` if TLS chain fails). PDFs: `https://www.in.gov/sboa/WebReports/{reportNumber}.pdf` |
| **ReClaw `sboa_ingest.py`** | Optional helper for same API — still cite the **public PDF URL**, not a local cache path as the only source |
| **DLGF budget orders** | `in.gov/dlgf/files/{year}-reports/{year}-budget-orders/{County}-…-Budget-Order.pdf` |
| **County wage ordinance** | County `*.in.gov` document center — OCR if scanned |

### Fortress / knowledge (supporting, not sole proof)
| Tool | Use for |
|------|---------|
| **reclaw-platform / ravenstack MCP** | `query_knowledge`, vault read, pipeline status — leads + prior packages |
| **county-audit skill** | When you need SBOA/Gateway tooling paths; **do not** ship flag-mill scripts as the Short |
| **openclaw-mechanic** | Only if Gateway/SBOA tooling is broken |
| **obsidian skill** | Optional vault mirror of the review card |

### Viral craft helpers
| Tool | Use for |
|------|---------|
| **imagine / image_edit** | Only for original map cards / lower-thirds concepts if asked — never fake “documents” |
| **pdf skill** | Merge/export packages if operator wants PDF |

**Hard ban as sources:** Salary.com, Glassdoor, OpenPayrolls, “average salary” blogs, Wikipedia alone for money claims, wrong-state newspapers.

---

## 2) County disambiguation (do this FIRST)

Many U.S. counties share names.

**Indiana-only primaries:**
- `gateway.ifionline.org`
- `audit.sboa.in.gov` / `in.gov/sboa/WebReports/`
- `in.gov/dlgf`
- `stats.indiana.edu`
- county `*.in.gov`

**Reject:** `.pa.gov`, out-of-state “Courier” with non-Indiana towns/commissioners, budgets that are 4× too large for a small rural IN county.

**Record in Meta:** FIPS + DLGF # (e.g. Pike = FIPS **18125**, DLGF **63**).

---

## 3) Viral interestingness filter (Track A + B)

Keep only facts that score high on **at least two**:

| Signal | Example |
|--------|---------|
| **Surprise** | Pattern break vs what people assume about rural counties |
| **Specificity** | Names + numbers + dates (not “long history of coal”) |
| **Rarity** | First after statehood, national median center, dual U.S. senators |
| **Emotional charge** | Hometown hero, fort on Buffalo Trace, tiny town SI |
| **Visual potential** | Map pin, rank graphic, $ big on screen, newspaper masthead |
| **Share trigger** | “Send this to someone from ___ County” / “I bet you didn’t know” |

Prefer **4–6 strong facts** over 12 weak ones. Drop leads that fail the bar into **Dropped / Weak**.

**Retention craft (for the script):**
- Cold open = **single strongest surprise** in ≤8 spoken words after “PIKE.” / “GIBSON.” etc.
- One idea per beat; on-screen cards ≤6 words when possible.
- Money section = **contrast** (e.g. paramedic > sheriff) or **YoY fund jump** or **filed SI $** — not a list of six middling salaries.
- Never open with method names (“IsolationForest found…”).

---

## 4) TRACK A — Interesting facts (history / geo / people)

**Pull:**
1. Census QuickFacts + Census Reporter — pop, density, median age, income, poverty, education  
2. STATS Indiana / IBRC — rank among 92 counties  
3. Census center-of-population releases when relevant (mean vs **median** — label correctly)  
4. `in.gov/ibc` county pages — firsts, notables  
5. Bioguide for senators/reps; IMH / GenWeb for settlement  
6. Digitized newspapers (Hoosier State Chronicles) only with **issue date + headline**

**Rules:** Prefer primary. Pin years. No invention. List **Research Gaps**.

**Output:** ranked facts + **one cold-open hook**.

---

## 5) TRACK B — Public money (verified kicker)

**Pull (priority):**
1. **Gateway Form 100R** — unit `{COUNTY} COUNTY` (+ towns if juice): Sheriff, Auditor, Commissioners, **top 5 earners**, dual lines  
2. **SBOA** — FINAL FILED only; prioritize report # ending in **`I`** (Special Investigation). Capture report ID + page + exact $  
3. **DLGF** certified budget orders (two years) — unit total + fund YoY (Highway, Election, General)  
4. **Wage/salary ordinance** — cross-check top salaries (OCR OK)  
5. Local news — **context only**, never sole proof  

**Rules (hard):**
- FACT register only. Never: fraud / stole / embezzled / “where did it go.”  
- Quote SBOA as filed: *overpayment*, *personal obligation*, *internal controls*, *requested reimburse*.  
- Every $ → exact number + URL (+ report ID/page).  
- **ClaimGate:** salary/finding needs a **2nd source** before **VERIFIED**.  
- No AFR fund rollups as “vendors.”  
- No estimator sites. Mark **UNVERIFIED** rather than guess.

### Named-individual judgment gate
Filed SI on a **named local person** can be fair-report legal — still default **HOLD** small-dollar neighbor findings for viral shorts unless the operator explicitly wants them. Prefer:

- Salary contrasts (title + $)  
- Fund YoY certified budgets  
- Unit totals  

over shaming a small-town clerk for mileage.

---

## 6) Assembly — viral Short structure (70–90 sec)

| Time | Content |
|------|---------|
| 0:00–0:03 | Cold open: “I bet you didn’t know this about…” / **COUNTY.** |
| 0:03–0:22 | History run — 3–4 fact beats (strongest first) |
| 0:22–0:48 | Money pivot: “Here’s the money — all public record.” 2–3 VERIFIED $ facts |
| 0:48–0:55 | Fair line: nothing claims wrongdoing; curiosity CTA to public records |
| 0:55–1:05 | Closer + “More Indiana county stories coming.” |

**On-screen:**
- Big $ ($92.5K not buried in a sentence)  
- Map pin / rank graphic  
- Lower-thirds: source short name (Census · Gateway 100R · DLGF · SBOA 84411I)  
- Faceless: TTS + public-domain / rights-clear pans — no stolen news clips  

**Script voice:** conversational, slightly conspiratorial curiosity, never screed.

---

## 7) Required deliverable package

Write **one** review card package (Markdown + optional phone HTML), then:

```bash
outbox-publish /root/outbox/YYYY-MM-DD-{COUNTY}-COUNTY-VIDEO-SHORTS.md \
  --title "{County} County Video Shorts package (YYYY-MM-DD)"
```

Also give:
- http://100.108.130.82:8765/
- http://100.108.130.82:8765/{filename}

### Package sections (exact order)

1. **Meta** — County, State=Indiana, FIPS, DLGF #, Confidence, Recommended (Short only | Short + optional long)  
2. **Ready-to-Record Short Script (70–90 sec)** — full VO text  
3. **Fact Table** — Spoken claim | Source URL | Why it scores | Visual suggestion  
4. **Money Table** — Claim | Exact $ | Name/Title | Source URL | Report ID/Page | VERIFIED?  
5. **End-card rank** — top 3–4 VERIFIED money/history combos for the final seconds  
6. **Asset List** — maps, headlines, rank graphics, PD photo ideas, music direction  
7. **Dropped / Weak** — leads + why  
8. **Research Gaps**  
9. **SA findings** (optional section if money track ran deep) — hooks + kills + citations  
10. **Publish gate checklist** — all boxes answered

---

## 8) Publish gate (never skip)

Human must be able to check:

- [ ] Every spoken claim has a public source URL  
- [ ] Zero fraud/criminal imputation language  
- [ ] County confirmed **Indiana** (FIPS/DLGF recorded)  
- [ ] Named-individual gate cleared or HOLD listed  
- [ ] Money $ dual-checked or marked UNVERIFIED  
- [ ] Outbox **index.html** top card linked via `outbox-publish`  
- [ ] No estimator / wrong-state contamination  

**Do not auto-publish** to YouTube/TikTok. Package only.

---

## 9) Run modes

| User says | You do |
|-----------|--------|
| “County video / shorts package for X” | Full Track A + B + script + outbox |
| “Just facts / cold open” | Track A only + script skeleton |
| “Just money / 100R / SBOA” | Track B table + end-card rank |
| “Next county in queue” | Prefer fortress `county-queue` tools if live; else ask which county |
| “Render / Remotion / upload” | Stop — package + gate only unless they explicitly want render tooling |

---

## 10) Lessons baked in (2026-07-29 Pike)

- Direct file URL ≠ visible outbox → always **`outbox-publish`**.  
- Gateway 100R needs **browser automation**, not scrape-only.  
- Scanned wage ordinances need **OCR**.  
- SBOA API body uses `counties` + `unitTypes`, not free-text only.  
- “Pike County Courier” can be **Pennsylvania** — disambiguate.  
- Paramedic > Sheriff and Election fund YoY were stronger viral money than flag-mills.  
- Small named SI: hold for ethics unless operator insists.

---

## 11) Quick start prompt (when operator names a county)

```
/county-video-shorts for {COUNTY} County, Indiana.
Full viral Shorts package: Track A facts + Track B money, primary sources only,
ClaimGate, ready-to-record 70–90s script, outbox-publish when done.
```

Begin research **now**. Return the package. No preamble fluff.

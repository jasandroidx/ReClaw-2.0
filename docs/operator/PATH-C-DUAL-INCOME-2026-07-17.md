# Path C — Dual income execution (operator plan)

**Decision:** Content primary (Story Factory / Silent Auditor) + thin local paid offer on the side.  
**Date:** 2026-07-17  
**Owner:** Human + Grok Build on this host  

---

## North star (both tracks)

| Track | Customer | You do | Agents do overnight |
|-------|----------|--------|---------------------|
| **Primary — Content** | YouTube/TikTok audience | Approve 1 story/package; publish | Research → filter → ClaimGate → script draft |
| **Side — Rural grant digest** | IN nonprofits / towns / rural biz | Send 1 email or PDF; collect $ | Public grant scan → ranked list → draft digest |

Human gates both. No auto-publish, no auto-outreach send.

---

## Primary: Story Factory (Silent Auditor)

### Done (this session + prior)

- [x] Freeze flag mill; truth rules + blueprint on disk  
- [x] Gateway-as-vendor hard-offs  
- [x] Playbook filter + reject → lesson  
- [x] SBOA ingest tool + cache for several counties  
- [x] **ClaimGate implemented** — `tools/claim_gate.py`  
  - Wired into `scriptwriter` (prefer ClaimGate-pass for shorts)  
  - Diagnostics in `silent_auditor` summary  
  - Tests: `tests/test_claim_gate.py` (green)

### Still required before unfreeze queue

| # | Item | Why |
|---|------|-----|
| 1 | **Dual-receipt pilot** (Winslow water template in `content_truth_rules.yaml`) | Pain leg + money leg in one short |
| 2 | **SBOA juice in package path** for next county run | ClaimGate-pass SBOA flags in the actual package |
| 3 | **Review card shows ClaimGate missing fields** | 60-second human decide |
| 4 | **You publish 1 short** outside the mill | Proof the loop pays (attention first) |
| 5 | Explicit **unfreeze** of `content_truth_rules.status` | Only after 1–3 cards you’d actually post |

### Primary weekly cadence (after unfreeze)

1. Overnight: one county package (or refresh after fixes)  
2. Morning: open review card — ClaimGate pass?  
3. Approve → publish short  
4. Reject with specific reason → lesson on disk  
5. Track: packages/week approved, posts live, views  

### Do not

- `run-next` / refresh while freeze is on  
- Approve Gibson/Posey-style mills to “get revenue”  
- Count flag volume as progress  

---

## Side: Thin grant digest (first paid offer)

**Offer (v0):** “Weekly Indiana rural grant / RFP shortlist — 5–10 fits with links + deadlines. $49/mo or free 2-week pilot.”

**Why this, not leads first:**  
Public sources, SOUL already exists (`agents/grant_watcher/SOUL.md`), lower ToS risk than marketplace scrape, clear buyer (nonprofit ED / town clerk / rural small biz).

### Build order (side)

| # | Item | Status |
|---|------|--------|
| 1 | Manual digest from public portals (you + one script) | Start here |
| 2 | `scripts/grant_digest_thin.py` → markdown in vault `pending_approval` | Scaffold next |
| 3 | 5 free pilots (email list you know) | Human send |
| 4 | Convert 1–2 paid | Real $ |
| 5 | Only then automate cron on gateway | |

**v0 content of a digest (one page):**

1. Title + week of  
2. 5 rows: program name | who should care | deadline | link | why rural IN  
3. Disclaimer: not legal/financial advice; verify on source site  
4. CTA: reply to keep getting this / $49/mo  

### Do not (side)

- Auto-apply to grants  
- Spam cold lists day one  
- Build full Grant Hall visual dungeon before first paid user  

---

## Sequencing (next 7–14 days)

| Day | Primary | Side |
|-----|---------|------|
| 1–2 | ClaimGate live (done); dual-receipt Winslow offline pilot | Draft digest template by hand |
| 3–4 | One county package with SBOA + ClaimGate-pass lead | Scrape/list 10 real grant links manually |
| 5 | You approve/reject; if good, **unfreeze** discussion | Send 3 free digests |
| 6–7 | First published short | Iterate digest from feedback |
| 8–14 | 2 more posts; measure | First paid ask |

---

## Success metrics (honest)

| Metric | Primary | Side |
|--------|---------|------|
| **Week 1** | 1 package you’d post | 1 digest PDF exists |
| **Week 2** | 1–3 shorts live | 3 people received free pilot |
| **Week 4** | Steady 2 packages/week approved | 1 paid or clear “no” from market |

If week 4 content has zero posts, primary is blocked on publish discipline — not agents.  
If week 4 side has zero interested humans, change offer — don’t add more agent rooms.

---

## Code map

| Piece | Path |
|-------|------|
| ClaimGate | `tools/claim_gate.py` |
| Truth rules / freeze | `data/content_truth_rules.yaml` |
| Workflow SOT | `docs/SILENT-AUDITOR-WORKFLOW.md` |
| SBOA | `tools/sboa_ingest.py` · `data/cache/sboa/` |
| Script prefer ClaimGate | `tools/scriptwriter.py` |
| Grant SOUL (not full agent yet) | `agents/grant_watcher/SOUL.md` |
| This plan | `docs/operator/PATH-C-DUAL-INCOME-2026-07-17.md` |

---

## Immediate next command for primary (when you say go)

```bash
# After dual-receipt pilot content exists, test ClaimGate on a real flag package:
cd /root/ReClaw-2.0
PYTHONPATH=. .venv/bin/python -c "
from tools.claim_gate import evaluate_claim, claim_gate_summary, filter_flags_through_claim_gate
# load flags from last package and print pass rate
"
# SBOA top-up for a pilot county:
./scripts/run_sboa_discovery.sh Clark
PYTHONPATH=. .venv/bin/python tools/sboa_ingest.py Clark --download-top 3
```

**Unfreeze is your call** after you see 1 card that meets ClaimGate and you’d put your name on the channel.

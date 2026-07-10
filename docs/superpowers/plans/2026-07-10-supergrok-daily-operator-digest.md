**Status:** Operator pack implemented 2026-07-10 (tools + docs). SuperGrok UI schedule remains human.

# SuperGrok Daily Operator Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a morning SuperGrok Automation that calls ReClaw MCP `project_sitrep`, produces a fixed six-block digest with human-only suggested actions, and document exact setup for the operator.

**Architecture:** Day-1 is prompt + docs + verification—no Hetzner cron, no auto-mutations. SuperGrok Automations schedules a fixed prompt that uses the existing `reclaw-platform` connector (`project_sitrep`). Optional Phase B.2 vault log is documented but not implemented until a later toggle.

**Tech Stack:** SuperGrok Automations (Tasks), ReClaw Platform MCP (`scripts/reclaw_platform_mcp_server.py`), Obsidian vault docs, Git.

**Spec:** `docs/superpowers/specs/2026-07-10-supergrok-daily-operator-digest-design.md`

---

## File map

| File | Responsibility |
|------|----------------|
| `docs/operator/SUPERGROK-DAILY-DIGEST.md` | Operator one-pager: schedule, connector checklist, exact prompt, acceptance |
| `docs/operator/prompts/morning-fortress-digest.txt` | Copy-paste-only prompt body (no prose) |
| `/root/obsidian_vault/Ravenstack/supergrok-daily-digest.md` | Vault mirror for `read_vault_file` / `connector_guide` cross-link |
| `Ravenstack/knowledge_index.md` (vault) | Index entry |
| `Ravenstack/super-grok-connector-guide.md` (vault) | Short pointer to daily digest setup |
| `docs/superpowers/specs/2026-07-10-supergrok-daily-operator-digest-design.md` | Already committed (read-only reference) |

No changes to OpenClaw gateway or pipeline for Phase B day 1.

---

### Task 1: Operator prompt file (exact contract)

**Files:**
- Create: `docs/operator/prompts/morning-fortress-digest.txt`
- Create: `docs/operator/` (directory)

- [ ] **Step 1: Create directory**

```bash
mkdir -p /root/ReClaw-2.0/docs/operator/prompts
```

- [ ] **Step 2: Write the prompt file exactly**

Create `docs/operator/prompts/morning-fortress-digest.txt` with this exact content (no YAML frontmatter):

```text
You are the ReClaw fortress morning operator. Use the ReClaw / reclaw-platform MCP connector.

1. Call project_sitrep (no arguments). Do not invent health. Do not simulate.
2. If county queue detail is missing from the sitrep, call pipeline_status.
3. Produce a report with EXACTLY these headings:
   ## 1. Overall
   ## 2. Stack (Docker / API / OpenClaw / MCP)
   ## 3. County queue
   ## 4. OpenClaw / models
   ## 5. Gaps
   ## 6. Actions
4. In Actions: give Top 3 operator actions, then a subsection
   ### SUGGESTED auto-actions (require human OK)
   Each suggestion must include: what / why / risk / exact approval phrase the human should type later.
   Do NOT run pipeline, approve queue, write vault, restart services, or any mutation.
5. If the connector fails: say DEGRADED, name the failure, tell the user to re-check the ReClaw connector URL (must end with /mcp; on server see data/mcp_public_url.txt). Do not claim success via Build paste-workarounds.
6. Prefer the sitrep plain-English content; light rephrase OK. No raw multi-page JSON dumps.
```

- [ ] **Step 3: Verify file**

```bash
wc -l /root/ReClaw-2.0/docs/operator/prompts/morning-fortress-digest.txt
test -s /root/ReClaw-2.0/docs/operator/prompts/morning-fortress-digest.txt && echo OK
```

Expected: `OK`, line count ≥ 15

- [ ] **Step 4: Commit**

```bash
cd /root/ReClaw-2.0
git add docs/operator/prompts/morning-fortress-digest.txt
git commit -m "docs: add SuperGrok morning fortress digest prompt"
```

---

### Task 2: Operator one-pager

**Files:**
- Create: `docs/operator/SUPERGROK-DAILY-DIGEST.md`

- [ ] **Step 1: Write the one-pager**

Create `docs/operator/SUPERGROK-DAILY-DIGEST.md` with:

```markdown
# SuperGrok Daily Fortress Digest

**Phase B day 1** · Report-only · You always approve mutations

## Schedule

- **When:** Morning America/Chicago (pick 7:00–9:00 local in SuperGrok Automations)
- **Where:** SuperGrok → Automations / Tasks
- **Connector:** ReClaw Platform MCP must be **on** for the task (same URL as chat, path ends `/mcp`)

## Setup (once)

1. Open SuperGrok → **Automations** (or Tasks).
2. **New automation** · Schedule: daily morning US.
3. Enable **ReClaw / reclaw-platform** connector for this automation if the UI has a connector picker.
4. Paste the entire contents of `docs/operator/prompts/morning-fortress-digest.txt` as the task prompt.
5. Enable push/email **if** SuperGrok offers it; otherwise open Automations history each morning (acceptable).
6. Run **once manually** to verify all six headings appear.

## If the connector fails

On the server:

```bash
cat /root/ReClaw-2.0/data/mcp_public_url.txt
curl -sf http://127.0.0.1:8100/health
systemctl is-active reclaw-mcp-bridge reclaw-mcp-tunnel
```

Update SuperGrok connector URL if the trycloudflare host rotated.

## Digest shape (required)

1. Overall  
2. Stack (Docker / API / OpenClaw / MCP)  
3. County queue  
4. OpenClaw / models  
5. Gaps  
6. Actions (+ SUGGESTED auto-actions require human OK)

## Never in this automation

- Approve/reject county queue  
- `run_pike_winslow`  
- Vault writes (day 1)  
- Docker restarts  
- Fake/simulated sitrep  

## After you approve a suggestion

Do it **manually** in SuperGrok chat or Build, e.g.:

- "Call pipeline_status and explain Gibson pending approval steps"  
- "I approve running Pike/Winslow" (only then use run tool)  
- County approve API / UI as documented in AGENTS.md  

## Related

- Spec: `docs/superpowers/specs/2026-07-10-supergrok-daily-operator-digest-design.md`  
- Prompt: `docs/operator/prompts/morning-fortress-digest.txt`  
- Vault: `Ravenstack/supergrok-daily-digest.md`  
- Skills: `project_sitrep`, `pipeline_status`, `connector_guide`
```

- [ ] **Step 2: Commit**

```bash
cd /root/ReClaw-2.0
git add docs/operator/SUPERGROK-DAILY-DIGEST.md
git commit -m "docs: SuperGrok daily digest operator one-pager"
```

---

### Task 3: Vault mirror + index

**Files:**
- Create: `/root/obsidian_vault/Ravenstack/supergrok-daily-digest.md`
- Modify: `/root/obsidian_vault/Ravenstack/knowledge_index.md`
- Modify: `/root/obsidian_vault/Ravenstack/super-grok-connector-guide.md` (add 5–10 line pointer only)

- [ ] **Step 1: Write vault mirror**

Create `/root/obsidian_vault/Ravenstack/supergrok-daily-digest.md`:

```markdown
# SuperGrok Daily Fortress Digest

**Purpose:** Morning operator automation using the ReClaw MCP connector.  
**Full operator guide (repo):** `docs/operator/SUPERGROK-DAILY-DIGEST.md`  
**Exact prompt:** `docs/operator/prompts/morning-fortress-digest.txt`  
**Design spec:** `docs/superpowers/specs/2026-07-10-supergrok-daily-operator-digest-design.md`

## In SuperGrok (manual once)

1. Automations → new daily morning task (America/Chicago).  
2. Paste prompt from repo file above (or ask Build for it).  
3. Connector: ReClaw platform enabled.  
4. Manual test run → six headings.

## Tools

- Required: `project_sitrep`  
- Optional: `pipeline_status`  
- Never day-1: mutations, vault write, queue approve  

## Human rule

Suggestions allowed. **You always OK** before any auto-action.

## Later (B.2)

Optional vault log via `save_ravenstack_note` — not enabled until you ask.

Cross-ref: [[super-grok-connector-guide]], [[openclaw-models-cheatsheet]], [[mcp-connector]]
```

- [ ] **Step 2: Index under Operational or Foundational**

Add to `knowledge_index.md` near SuperGrok / MCP entries:

```markdown
- [[supergrok-daily-digest.md|SuperGrok Daily Digest]] — Morning Automation: sitrep + queue + OpenClaw health; human OK for actions.
```

- [ ] **Step 3: Pointer in connector guide**

At end of `super-grok-connector-guide.md` (or under a "Daily automation" heading), add:

```markdown
## Daily automation (Phase B)

Morning SuperGrok Task: [[supergrok-daily-digest]].  
Prompt lives in repo `docs/operator/prompts/morning-fortress-digest.txt`.  
Always human-approved mutations only.
```

- [ ] **Step 4: Commit vault**

```bash
cd /root/obsidian_vault
git add Ravenstack/supergrok-daily-digest.md Ravenstack/knowledge_index.md Ravenstack/super-grok-connector-guide.md
git commit -m "ravenstack: SuperGrok daily digest operator note"
git push origin HEAD
```

- [ ] **Step 5: Commit repo if any vault path was mirrored under docs only** (vault is separate repo; already done in step 4)

---

### Task 4: Smoke-test MCP tools (server)

**Files:** none (verification only)

- [ ] **Step 1: Health**

```bash
curl -sf http://127.0.0.1:8100/health
systemctl is-active reclaw-mcp-bridge reclaw-mcp-tunnel
cat /root/ReClaw-2.0/data/mcp_public_url.txt
```

Expected: `status":"ok"`, both `active`, URL ends with `/mcp`

- [ ] **Step 2: project_sitrep returns plain English with sections**

```bash
cd /root/ReClaw-2.0
.venv/bin/python - <<'PY'
import importlib.util, os
os.environ.pop("RECLAW_GATEWAY_TOKEN", None)
spec = importlib.util.spec_from_file_location("p", "scripts/reclaw_platform_mcp_server.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
text = m.project_sitrep()
assert "Overall" in text or "overall" in text.lower() or "Sitrep" in text
assert not text.lstrip().startswith("{")
print("sitrep_ok", len(text), text.splitlines()[0][:80])
PY
```

Expected: `sitrep_ok` and first line is markdown heading, not `{`

- [ ] **Step 3: Commit nothing if only verification** — if health broken, fix bridge before claiming Phase B done

---

### Task 5: Operator acceptance checklist (doc)

**Files:**
- Modify: `docs/operator/SUPERGROK-DAILY-DIGEST.md` — append Acceptance section if not already complete from Task 2

- [ ] **Step 1: Ensure Acceptance section exists**

Append if missing:

```markdown
## Acceptance (operator)

- [ ] Manual task run produces headings 1–6  
- [ ] SUGGESTED auto-actions present or explicit "none"  
- [ ] No pipeline/queue/vault mutations in the run  
- [ ] Connector failure path tested once (disable connector → DEGRADED)  
- [ ] Morning schedule saved in SuperGrok Automations  
```

- [ ] **Step 2: Commit**

```bash
cd /root/ReClaw-2.0
git add docs/operator/SUPERGROK-DAILY-DIGEST.md
git commit -m "docs: acceptance checklist for SuperGrok daily digest"
```

---

### Task 6: Push ReClaw + final status

**Files:** none

- [ ] **Step 1: Push**

```bash
cd /root/ReClaw-2.0
git push origin HEAD
git log -3 --oneline
git status -sb
```

Expected: clean of digest-related files; `open-swe/` may remain untracked (ignore)

- [ ] **Step 2: Tell operator the SuperGrok UI steps (human)**

Operator must:

1. Open SuperGrok Automations  
2. Paste prompt from `docs/operator/prompts/morning-fortress-digest.txt`  
3. Run once manually  
4. Confirm six headings  

Agent cannot complete SuperGrok UI clicks.

---

## Spec coverage check

| Spec requirement | Task |
|------------------|------|
| Morning SuperGrok Task + connector | 1, 2, 6 |
| Six digest blocks | 1, 2 |
| project_sitrep required | 1, 4 |
| Suggestions require human OK | 1, 2 |
| No day-1 mutations | 1, 2 |
| Push/email if possible; history OK | 2 |
| Vault log later only | 2, 3 |
| Failure DEGRADED | 1, 4 |
| Connector URL rotate | 2, 4 |

## Placeholder scan

No TBD steps. SuperGrok UI is explicitly human-only (Task 6).

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-10-supergrok-daily-operator-digest.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with checkpoints  

**Which approach?**

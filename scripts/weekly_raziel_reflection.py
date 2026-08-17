import os
import glob
import json
import urllib.request
import datetime

VAULT_DIR = "/root/obsidian_vault/Ravenstack/ops/audits"
OBSERVATIONAL_FILE = "/root/obsidian_vault/Ravenstack/memory/OBSERVATIONAL.md"
today = datetime.date.today().isoformat()
audit_file = f"{VAULT_DIR}/Weekly-Audit-{today}.md"
reflection_file = f"{VAULT_DIR}/Weekly-Reflection-{today}.md"


def _extract_briefing(reflection_text):
    """Pull the short 'Morning Briefing Summary' out of the full reflection."""
    marker = "## Morning Briefing Summary"
    idx = reflection_text.find(marker)
    if idx == -1:
        first_line = reflection_text.strip().splitlines()[0] if reflection_text.strip() else ""
        return first_line[:200] or "(no summary produced)"
    tail = reflection_text[idx + len(marker):].strip()
    next_heading = tail.find("\n## ")
    if next_heading != -1:
        tail = tail[:next_heading]
    return tail.strip()


def _share_to_observational(reflection_text):
    """Append a dated pointer to OBSERVATIONAL.md so a future 'read vault'
    session actually surfaces this instead of it sitting unread in
    ops/audits/ (see 2026-08-17: two weeks of reflections nobody saw)."""
    try:
        briefing = _extract_briefing(reflection_text)
        entry = (
            f"\n### {today} - Raziel weekly reflection\n"
            f"- {briefing}\n"
            f"- Full reflection: `{reflection_file}`\n"
        )
        with open(OBSERVATIONAL_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        marker = "## Latest\n"
        idx = content.find(marker)
        if idx == -1:
            print(f"[-] Could not find '## Latest' in {OBSERVATIONAL_FILE}; skipping share-back.")
            return
        insert_at = idx + len(marker)
        with open(OBSERVATIONAL_FILE, "w", encoding="utf-8") as f:
            f.write(content[:insert_at] + entry + content[insert_at:])
        print(f"[SUCCESS] Shared pointer into {OBSERVATIONAL_FILE}")
    except Exception as e:
        print(f"[-] Could not share reflection pointer to OBSERVATIONAL.md: {e}")


def main():
    if not os.path.exists(audit_file):
        print(f"[-] No audit file found at {audit_file}. Skipping reflection.")
        return

    with open(audit_file, "r", encoding="utf-8") as f:
        audit_content = f.read()

    # Formulate reflection prompt for Raziel
    prompt = f"""You are Raziel performing your scheduled weekly self-improvement audit.

Review this weekly system audit and failure ledger:
---
{audit_content}
---

Your task:
1. Analyze any logged friction points (like tool discovery errors, search biases, or gateway timeouts).
2. Propose 1-2 concrete, high-signal improvements (e.g., an OpenClaw skill proposal, a truth rule update in content_truth_rules.yaml, or a workflow fix).
3. Format your response clearly under:
   - ## Root Cause Analysis
   - ## Proposed Fixes / Staged Skills
   - ## Morning Briefing Summary (1-2 sentences to present to Jason)

Keep it direct, logical, and actionable."""

    # Call local Ollama or ReClaw API gateway
    payload = {
        "model": "gemma4",
        "prompt": prompt,
        "stream": False
    }

    print("[*] Dispatching reflection job to local model...")
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            reflection_text = data.get("response", "")

            with open(reflection_file, "w", encoding="utf-8") as rf:
                rf.write(f"# Raziel Weekly Reflection & Upgrade Proposals ({today})\n\n{reflection_text}\n")
            print(f"[SUCCESS] Reflection generated: {reflection_file}")
            _share_to_observational(reflection_text)
    except Exception as e:
        print(f"[-] Reflection job error (Ollama fallback): {e}")

if __name__ == "__main__":
    main()

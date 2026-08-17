import os
import glob
import json
import urllib.request
import datetime

VAULT_DIR = "/root/obsidian-vault/Ravenstack/ops/audits"
today = datetime.date.today().isoformat()
audit_file = f"{VAULT_DIR}/Weekly-Audit-{today}.md"
reflection_file = f"{VAULT_DIR}/Weekly-Reflection-{today}.md"

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
    except Exception as e:
        print(f"[-] Reflection job error (Ollama fallback): {e}")

if __name__ == "__main__":
    main()

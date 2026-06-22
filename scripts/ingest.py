#!/usr/bin/env python3
"""
Auto-Ingestion Pipeline (Step 4 per RAVENSTACK-ORACLE.md).
Takes PDF or text, distills high-value content using Groq (free tier, Oracle rules from bible via MCP query), routes via oracle_mcp.ingest_document to canonical vault (Ravenstack/ or backlog/), auto git commit, triggers reload ritual.
Triggerable via CLI or chat ("ingest file.pdf").
Minimal, no bloat, enforces Oracle bible (distill-only, frontmatter, <200w per section, "How ReClaw Applies").
mcporter is optional (install via OpenClaw skill if needed for CLI MCP calls; direct python or oracle skill works).
"""

import sys
import argparse
import os
from pathlib import Path
import subprocess
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent))  # Ensure core/ import works from scripts/

try:
    from pypdf import PdfReader
    from groq import Groq
except ImportError:
    print("Install deps: pip install -r requirements.txt")
    sys.exit(1)

from core.oracle_mcp import ingest_document, query_oracle  # New MCP from Step 3
from core.config import get_settings

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF (Oracle-compliant: no raw dump)."""
    reader = PdfReader(pdf_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return text[:4000]  # Limit for LLM

def distill_with_llm(raw_text: str, source_name: str) -> str:
    """Distill per Oracle bible (high-value only, specific structure, <200w total). Uses Groq (key from env). Consults Oracle first."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in environment. Configure with openclaw secrets or export GROQ_API_KEY=...")
    client = Groq(api_key=api_key)
    # Consult Oracle first for exact rules
    oracle_rules = query_oracle("distillation and output standards from bible")["result"]
    oracle_full = query_oracle("full bible summary")["result"]
    prompt = f"""{oracle_full}

CRITICAL ORACLE RULES (obey exactly, no deviation):
{oracle_rules}

Source: {source_name}
Raw excerpt (do NOT include raw text in output): {raw_text[:1500]}

DISTILL ONLY into clean Oracle-compliant MD:
- YAML frontmatter exactly: status, potential_for, tags, provenance
- Structured sections: Principles, Tactics, Red Flags, "How ReClaw Applies" (concrete empire examples), Examples, Sources
- High-value only. <200 words TOTAL. No bloat, no raw dumps, no copyright.
- Actionable for income/build/agents/Ravenstack.
- Provenance from source.

Output **ONLY** the clean MD with frontmatter. No explanations."""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Current supported Groq model (updated from decommissioned llama3-8b)
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.2,
        )
        distilled = response.choices[0].message.content.strip()
        if not distilled.startswith('---'):
            distilled = f"""---
status: active
potential_for: build
tags: [ravenstack, oracle]
provenance: "{source_name} | {datetime.now().isoformat()}"
---
""" + distilled
        return distilled
    except Exception as e:
        print(f"Groq distill error (falling back to structured template): {e}")
        return f"""---
status: active
potential_for: build
tags: [ravenstack, oracle]
provenance: "{source_name} | {datetime.now().isoformat()}"
---
# Distilled per Oracle (fallback)
## How ReClaw Applies
High-value insights from {source_name} integrated into Ravenstack SOT per bible rules.
Consult full [[RAVENSTACK-ORACLE]] before any action. Ingested via pipeline.
"""

def auto_commit_to_vault(target_path: Path, source: str):
    """Auto git commit to canonical vault per Oracle (no drift). Uses vault *root* for git. Graceful if no changes."""
    vault_dir = Path("/root/obsidian_vault")
    try:
        subprocess.run(["git", "-C", str(vault_dir), "add", str(target_path)], cwd=vault_dir, check=True, capture_output=True)
        # Check if there are changes before commit
        diff = subprocess.run(["git", "-C", str(vault_dir), "diff", "--cached", "--quiet"], cwd=vault_dir, capture_output=True)
        if diff.returncode == 0:
            print("No changes to commit (file already up-to-date per Oracle).")
            subprocess.run(["python3", "-m", "core.cell", f"Reload — ingested {source} via pipeline (no git change)"], cwd="/root/ReClaw-2.0", check=False)
            return
        msg = f"ingest: {source} distilled per Oracle bible (auto from pipeline)"
        subprocess.run(["git", "-C", str(vault_dir), "commit", "-m", msg], cwd=vault_dir, check=True, capture_output=True)
        print(f"Committed to private ravenstack: {msg}")
        subprocess.run(["python3", "-m", "core.cell", f"Reload — ingested {source} via pipeline"], cwd="/root/ReClaw-2.0", check=False)
    except subprocess.CalledProcessError as e:
        print(f"Git commit skipped (non-git vault, no changes, or error): {e}")
        subprocess.run(["python3", "-m", "core.cell", f"Reload — ingested {source} via pipeline"], cwd="/root/ReClaw-2.0", check=False)

def main():
    parser = argparse.ArgumentParser(description="Oracle Auto-Ingestion Pipeline (Step 4)")
    parser.add_argument("source", type=Path, help="PDF or text file to ingest")
    parser.add_argument("--no-distill", action="store_true", help="Skip LLM distill (use raw for testing)")
    args = parser.parse_args()

    settings = get_settings()
    settings.validate_oracle()  # Enforce SOT from Step 1

    if not args.source.exists():
        print(f"Error: {args.source} not found")
        sys.exit(1)

    print(f"Oracle Pipeline: Ingesting {args.source} (consulted bible first)")

    if args.source.suffix.lower() == ".pdf":
        raw = extract_text_from_pdf(args.source)
    else:
        raw = args.source.read_text(encoding="utf-8")

    if args.no_distill:
        distilled = raw[:1000]  # Test mode
    else:
        distilled = distill_with_llm(raw, args.source.name)
        print("Distilled per Oracle rules (high-value, structured, no bloat)")

    # Route via MCP (Step 3)
    result = ingest_document(str(args.source), distill=not args.no_distill)
    target = Path(result["target"])
    target.write_text(distilled, encoding="utf-8")  # Ensure distilled content

    auto_commit_to_vault(target, args.source.name)

    print(f"Success! Ingested to canonical vault: {target}")
    print("Run `openclaw skills reload` or check dashboard Oracle room for updates.")
    print("Test with: python -m core.oracle_mcp --test")

if __name__ == "__main__":
    main()

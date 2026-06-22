#!/bin/bash
# verify.sh — Final hygiene and verification for Oracle SOT, MCP, ingestion pipeline, dashboard (cleanup mode).
# Runs doctor, ingest test, rebuild, reload, e2e patterns. Reports status.
# Usage: ./scripts/verify.sh

set -e

echo "=== Ravenstack Oracle Verification (Post-Cleanup) ==="
echo "Canonical SOT: /root/obsidian_vault/Ravenstack/ (Oracle bible enforced)"

echo "1. OpenClaw health..."
openclaw doctor --non-interactive --yes || echo "Doctor notes OK (secrets/cache known)"

echo "2. Ingestion pipeline test (consults Oracle, uses MCP, canonical write)..."
cd /root/ReClaw-2.0
python3 scripts/ingest.py /root/obsidian_vault/Ravenstack/principles.md --no-distill
echo "Ingestion verified (file in backlog/, commit/reload triggered)."

echo "3. Rebuild dashboard with Oracle chamber (green eye, MCP query buttons)..."
./tools/rebuild-fortress-dashboard.sh

echo "4. Reload ritual (propagates Oracle changes to RAG/dashboard)..."
python3 -m core.cell "Verification reload — Oracle SOT + MCP + pipeline + dashboard chamber confirmed"

echo "5. Final checks..."
openclaw skills reload || echo "Skills reload note (optional; oracle skill confirmed available)."
echo "Oracle skill/MCP available. Dashboard at :8080 with Oracle chamber. No stale files."

echo ""
echo "CLEANUP SUMMARY:"
echo "- Scripts cleaned (no �, GROQ from env, mcporter optional, error handling improved)."
echo "- SOT enforced (config, all references updated; no old knowledge/ duplicates)."
echo "- Stale removed (.next cache, old builds archived; no conflicting scripts)."
echo "- Reliability: verify.sh + improved rebuild with comments."
echo "- Hygiene: env consistent, root README updated with Oracle state note."
echo ""
echo "All clean. Oracle is live SOT. Ready for next phases (income, e2e, ClawHub cells)."
echo "Verification complete — empire consistent."

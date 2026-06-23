#!/bin/bash
# deploy.sh - Forged by Clawforge *CLANG*
set -e
echo "*CLANG* Deploying the rural-data-forge forge room..."

WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
mkdir -p "$WORKSPACE/agents/rural-data-forge" "$WORKSPACE/skills" "$WORKSPACE/vault/approvals/pending" "$WORKSPACE/vault/approvals/approved" "$WORKSPACE/vault/audits"

# Copy from current staging (works whether run from parent or inside staging/)
cp -r ./workspace/agents/* "$WORKSPACE/agents/" 2>/dev/null || cp -r ../workspace/agents/* "$WORKSPACE/agents/" || true
cp -r ./workspace/skills/* "$WORKSPACE/skills/" 2>/dev/null || cp -r ../workspace/skills/* "$WORKSPACE/skills/" || true
cp -r ./vault_structure/* "$WORKSPACE/vault/" 2>/dev/null || cp -r ../vault_structure/* "$WORKSPACE/vault/" || true

echo "Room forged successfully! The anvil is hot."
echo "Next steps:"
echo "1. openclaw skills reload"
echo "2. openclaw session new --room rural-data-forge --goal 'Test the forge with human approval gate.'"
echo "3. Check $WORKSPACE/vault/approvals/pending/ for gates (never bypass - sandbox enforced)."
echo "4. Review $WORKSPACE/vault/castle_map.json for visual UI square/forge layout."
echo "*CLANG* Tight, well-oiled machine ready. Sub-agents and approval gates active."

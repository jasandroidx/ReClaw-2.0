#!/usr/bin/env bash
# GATED PC-hands demo — run ON BoydsComp after reading the job card.
# Human gate: you run this only when you intend to produce a deliverable.
#
# What it does:
#  1. Collects safe local facts (hostname, time, disk, openclaw node status)
#  2. Writes a markdown package in ~/fortress-hands/
#  3. SCPs it to fortress /root/outbox/ and runs outbox-publish over SSH
#
# Usage:
#   bash boydscomp-pc-hands-demo.sh
# Optional:
#   FORTRESS=root@100.108.130.82 bash boydscomp-pc-hands-demo.sh
set -euo pipefail

FORTRESS="${FORTRESS:-root@100.108.130.82}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DIR="${HOME}/fortress-hands"
mkdir -p "$DIR"
OUT="${DIR}/pc-hands-demo-${STAMP}.md"
TITLE="PC hands demo — BoydsComp ${STAMP}"

{
  echo "# ${TITLE}"
  echo
  echo "_Generated on the Linux PC node · human-gated · no county pipeline_"
  echo
  echo "## Machine"
  echo
  echo "- hostname: \`$(hostname)\`"
  echo "- user: \`$(whoami)\`"
  echo "- UTC: \`$(date -u +%Y-%m-%dT%H:%M:%SZ)\`"
  echo "- local: \`$(date +%Y-%m-%dT%H:%M:%S%z)\`"
  echo "- kernel: \`$(uname -srmo 2>/dev/null || uname -a)\`"
  echo
  echo "## Disk (home + root if visible)"
  echo
  echo '```'
  df -h "$HOME" / 2>/dev/null | head -20 || df -h
  echo '```'
  echo
  echo "## OpenClaw node (local)"
  echo
  echo '```'
  if command -v openclaw >/dev/null 2>&1; then
    openclaw --version 2>&1 || true
    openclaw node status 2>&1 || true
  else
    echo "openclaw not on PATH"
  fi
  echo '```'
  echo
  echo "## Tailscale (if present)"
  echo
  echo '```'
  if command -v tailscale >/dev/null 2>&1; then
    tailscale status 2>&1 | head -15 || true
    tailscale ip -4 2>&1 || true
  else
    echo "tailscale not on PATH"
  fi
  echo '```'
  echo
  echo "## Why this exists"
  echo
  echo "Proves **Hetzner gateway + BoydsComp node** can produce an operator-facing"
  echo "artifact from the PC and land it in the permanent outbox — without"
  echo "unfreezing Story Factory or auto-running county packages."
  echo
  echo "## Next cool upgrades (not done by this script)"
  echo
  echo "1. Browser proxy / signed-in Chrome jobs on this node"
  echo "2. Local Ollama bulk jobs"
  echo "3. Default exec → node only when Jason opts in"
  echo
  echo "status: ok"
  echo
} >"$OUT"

echo "WROTE $OUT"
echo "=== preview ==="
head -40 "$OUT"
echo "..."

echo "=== ship to fortress outbox ==="
scp -o BatchMode=yes -o ConnectTimeout=10 "$OUT" "${FORTRESS}:/root/outbox/" || {
  echo "SCP failed. Is SSH key set up to ${FORTRESS}?"
  echo "Manual: copy $OUT to fortress /root/outbox/ then:"
  echo "  outbox-publish /root/outbox/$(basename "$OUT") --title \"$TITLE\""
  exit 1
}

BASE="$(basename "$OUT")"
ssh -o BatchMode=yes -o ConnectTimeout=10 "$FORTRESS" \
  "outbox-publish /root/outbox/${BASE} --title $(printf %q "$TITLE") && chmod 644 /root/outbox/${BASE}" || {
  echo "outbox-publish over SSH failed — file may still be in /root/outbox/${BASE}"
  exit 1
}

echo
echo "DONE."
echo "  Local:  $OUT"
echo "  Outbox: http://100.108.130.82:8765/${BASE}"
echo "  Home:   http://100.108.130.82:8765/"

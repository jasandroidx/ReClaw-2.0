#!/usr/bin/env bash
# Tier-3 audit tool discovery — Firecrawl search + cache to .firecrawl/
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
source .env 2>/dev/null || true
set +a
: "${FIRECRAWL_API_KEY:?FIRECRAWL_API_KEY missing in .env}"

mkdir -p .firecrawl data/cache/firecrawl

QUERIES=(
  "site:github.com government vendor payment audit python duplicate"
  "site:github.com benford law forensic accounting python MAD"
  "site:github.com public procurement anomaly detection"
  "Indiana SBOA audit reports county"
  "open source municipal check register fraud detection"
)

for q in "${QUERIES[@]}"; do
  slug=$(echo "$q" | tr ' ' '-' | tr -cd 'a-zA-Z0-9-' | cut -c1-48)
  echo "==> $q"
  firecrawl search "$q" --limit 8 -o ".firecrawl/discover-${slug}.json" || true
done

echo "Discovery complete. Review .firecrawl/ and update data/audit_tool_candidates.yaml"
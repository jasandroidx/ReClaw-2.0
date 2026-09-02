#!/usr/bin/env bash
# Render Project ReClaw HHVCTA short from manifest JSON → MP4
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="${1:-$ROOT/data/manifests/gibson/manifest_gibson.json}"
OUT="${2:-$ROOT/render/remotion/out/reclaw-audit.mp4}"

cd "$ROOT/render/remotion"
if [[ ! -d node_modules ]]; then
  npm install
fi
node scripts/render-manifest.mjs "$MANIFEST" "$OUT"
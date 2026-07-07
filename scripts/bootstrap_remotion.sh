#!/usr/bin/env bash
# Bootstrap Remotion render stack on Hetzner (Project ReClaw).
# Project lives at render/remotion/ — equivalent to create-video + ReclawComposition.tsx.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/render/remotion"

if [[ ! -f package.json ]]; then
  echo "[!] render/remotion missing — run: npx create-video@latest (Tailwind template), then copy ReclawComposition.tsx"
  exit 1
fi

npm install
npx remotion bundle src/index.ts
echo "[+] Remotion ready. Render: PYTHONPATH=$ROOT .venv/bin/python $ROOT/scripts/run_remotion_orchestrator.py --county Gibson"
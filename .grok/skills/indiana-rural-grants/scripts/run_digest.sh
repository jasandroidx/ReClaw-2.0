#!/usr/bin/env bash
# Thin wrapper for indiana-rural-grants skill.
# Usage: run_digest.sh [query] [limit]
set -euo pipefail
ROOT="/root/ReClaw-2.0"
QUERY="${1:-beekeeping greenhouse specialty crop rural Indiana}"
LIMIT="${2:-8}"
cd "$ROOT"
export PYTHONPATH=.
exec .venv/bin/python scripts/grant_digest_thin.py --query "$QUERY" --limit "$LIMIT"

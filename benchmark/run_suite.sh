#!/usr/bin/env bash
set -euo pipefail

# Helper script for running the Ollama CPU-Safe Benchmark Harness

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

echo "=== Ollama CPU-Safe Benchmark Harness ==="
python3 "${SCRIPT_DIR}/run_suite.py" "$@"

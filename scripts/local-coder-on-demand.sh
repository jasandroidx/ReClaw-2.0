#!/usr/bin/env bash
# Start/stop the local qwen2.5-coder llama-server (port 8080) when needed.
# Default: OFF (saves ~8GB RAM + CPU for overnight Raziel/Ollama).
set -euo pipefail
case "${1:-status}" in
  start) systemctl start llama-brain.service; systemctl status llama-brain.service --no-pager | head -12 ;;
  stop)  systemctl stop llama-brain.service; free -h | head -3 ;;
  status) systemctl is-active llama-brain.service; ss -tlnp | rg 8080 || true; free -h | head -3 ;;
  *) echo "usage: $0 start|stop|status"; exit 2 ;;
esac

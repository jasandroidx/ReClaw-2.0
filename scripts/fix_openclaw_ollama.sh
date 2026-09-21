#!/usr/bin/env bash
# One command: fix Ollama model discovery, restart the gateway, verify.
#
#   bash scripts/fix_openclaw_ollama.sh
#
# Why this is needed -- docs.openclaw.ai/providers/ollama/model-discovery:
#   "A nonempty models.providers.ollama.models list selects manual models
#    and skips discovery."
# The hand-written 3-model list is what hides the other pulled tags. Emptying
# it hands the job back to discovery, permanently.
#
# Safe: the python step backs up openclaw.json, re-parses the result before
# replacing it, and leaves cloud providers alone. Stops at the first failure.

set -euo pipefail

CFG="${OPENCLAW_CONFIG:-$HOME/.openclaw/openclaw.json}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=============================================="
echo " 1/5  config: $CFG"
echo "=============================================="
if [ ! -f "$CFG" ]; then
  echo "FAIL: no config at $CFG" >&2
  echo "      Set OPENCLAW_CONFIG=/path/to/openclaw.json and re-run." >&2
  exit 1
fi
python3 - "$CFG" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding="utf-8"))
def walk(n, path=""):
    if isinstance(n, dict):
        for k, v in n.items():
            here = f"{path}.{k}" if path else k
            if isinstance(v, dict) and (k == "ollama" or v.get("api") == "ollama"):
                ms = v.get("models")
                ids = [m.get("id", m.get("name", "?")) if isinstance(m, dict) else str(m)
                       for m in (ms if isinstance(ms, list) else [])]
                print(f"  {here}: baseUrl={v.get('baseUrl','(unset)')} models={len(ids)} {ids}")
            yield from () or walk(v, here)
    elif isinstance(n, list):
        for i, v in enumerate(n):
            yield from () or walk(v, f"{path}[{i}]")
list(walk(d))
PY

echo
echo "=============================================="
echo " 2/5  dry run"
echo "=============================================="
python3 "$HERE/fix_ollama_discovery.py" --config "$CFG"

echo
echo "=============================================="
echo " 3/5  applying"
echo "=============================================="
python3 "$HERE/fix_ollama_discovery.py" --config "$CFG" --apply

echo
echo "=============================================="
echo " 4/5  restarting gateway"
echo "=============================================="
docker restart openclaw-gateway
for i in $(seq 1 30); do
  if docker inspect -f '{{.State.Health.Status}}' openclaw-gateway 2>/dev/null | grep -q healthy; then
    echo "gateway healthy after ${i}0s"
    break
  fi
  sleep 10
done

echo
echo "=============================================="
echo " 5/5  verify -- all pulled tags should appear"
echo "=============================================="
echo "--- ollama has: ---"
curl -s http://127.0.0.1:11434/api/tags | python3 -c \
  "import json,sys; print('\n'.join('  '+m['name'] for m in json.load(sys.stdin).get('models',[])))" \
  2>/dev/null || echo "  (could not reach ollama on 127.0.0.1:11434)"
echo "--- openclaw sees: ---"
openclaw models list 2>&1 | sed 's/^/  /' || echo "  (openclaw CLI not on PATH -- run it inside the container)"

echo
echo "Done. NOTE: the openclaw_models MCP tool reads openclaw.json, so it will"
echo "now show the ollama provider EMPTY. That is correct -- the list is empty"
echo "on purpose and discovery fills the live registry. 'openclaw models list'"
echo "above is the real check."

#!/usr/bin/env bash
# Add the missing Ollama tags to OpenClaw, WITH a rollback that actually fires.
#
#   bash scripts/openclaw_safe_apply.sh
#
# The previous attempt emptied models: [] and the gateway exited 78 (EX_CONFIG),
# leaving it in a restart loop until a human reverted by hand. This will not do
# that: it validates before restarting, and if the gateway does not come back
# healthy it restores the backup and restarts again by itself.
#
# Order: back up -> surgical edit -> doctor -> restart -> health-wait
#        -> automatic rollback on any failure.

set -uo pipefail

CFG="${OPENCLAW_CONFIG:-$HOME/.openclaw/openclaw.json}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
SAFE="$CFG.safe-$STAMP"

die() { echo "FAIL: $*" >&2; exit 1; }

[ -f "$CFG" ] || die "no config at $CFG"

# Our own known-good copy, independent of the python script's backup.
cp "$CFG" "$SAFE" || die "could not back up"
echo "known-good copy: $SAFE"

rollback() {
  echo
  echo "!!! ROLLING BACK -- restoring $SAFE"
  cp "$SAFE" "$CFG"
  docker restart openclaw-gateway >/dev/null 2>&1
  for _ in $(seq 1 24); do
    if [ "$(docker inspect -f '{{.State.Health.Status}}' openclaw-gateway 2>/dev/null)" = "healthy" ]; then
      echo "gateway healthy again on the previous config."
      echo "Nothing was changed. Send the doctor/log output above to Claude."
      exit 1
    fi
    sleep 5
  done
  die "gateway did NOT recover. Restore by hand: cp $SAFE $CFG && docker restart openclaw-gateway"
}

echo
echo "=== 1/4  dry run ==="
python3 "$HERE/openclaw_add_ollama_models.py" --config "$CFG" || die "dry run failed -- nothing written"

echo
echo "=== 2/4  applying (surgical splice, JSON5-safe) ==="
python3 "$HERE/openclaw_add_ollama_models.py" --config "$CFG" --apply || die "apply failed -- nothing written"

echo
echo "=== 3/4  validating BEFORE restart (openclaw doctor) ==="
DOC=""
if docker exec openclaw-gateway openclaw doctor >/tmp/oc_doctor.txt 2>&1; then
  DOC=ok
elif openclaw doctor >/tmp/oc_doctor.txt 2>&1; then
  DOC=ok
fi
sed 's/^/  /' /tmp/oc_doctor.txt 2>/dev/null | tail -30
if [ "$DOC" != "ok" ]; then
  echo
  echo "doctor reported problems (or could not run)."
  echo "Note: a host.docker.internal lint failure is a KNOWN false positive on"
  echo "Linux containers and is not caused by this change."
  read -r -p "Continue and restart anyway? [y/N] " a
  [ "${a:-N}" = "y" ] || { cp "$SAFE" "$CFG"; echo "reverted, gateway untouched."; exit 1; }
fi

echo
echo "=== 4/4  restart + health wait (auto-rollback on failure) ==="
docker restart openclaw-gateway || rollback
for i in $(seq 1 24); do
  st="$(docker inspect -f '{{.State.Health.Status}}' openclaw-gateway 2>/dev/null || echo missing)"
  run="$(docker inspect -f '{{.State.Status}}' openclaw-gateway 2>/dev/null || echo missing)"
  echo "  ${i}: status=$run health=$st"
  case "$run" in
    restarting|exited|dead) echo "  gateway is failing to start."; rollback ;;
  esac
  [ "$st" = "healthy" ] && { echo "  gateway healthy."; break; }
  [ "$i" = "24" ] && { echo "  never became healthy."; rollback; }
  sleep 5
done

echo
echo "=== result ==="
echo "--- ollama has: ---"
curl -s http://127.0.0.1:11434/api/tags | python3 -c \
  "import json,sys; print('\n'.join('  '+m['name'] for m in json.load(sys.stdin).get('models',[])))" \
  2>/dev/null || echo "  (could not reach ollama)"
echo "--- openclaw sees: ---"
(docker exec openclaw-gateway openclaw models list 2>&1 || openclaw models list 2>&1) | sed 's/^/  /' | head -30

echo
echo "Success. Known-good copy kept at: $SAFE"
echo "Manual revert if you ever want it:"
echo "  cp $SAFE $CFG && docker restart openclaw-gateway"

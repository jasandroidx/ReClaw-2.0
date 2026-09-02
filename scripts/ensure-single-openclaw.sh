#!/usr/bin/env bash
# ReClaw: enforce ONE OpenClaw gateway — Docker compose `openclaw-gateway` only.
# Duplicates (host `openclaw gateway`, second containers, user systemd) break Discord,
# sessions, config watches, and Tailscale Serve. This script is the guard.
set -euo pipefail

# systemd oneshot often has no HOME under set -u
export HOME="${HOME:-/root}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

USER_UNIT_DIR="${HOME}/.config/systemd/user"
USER_UNIT="${USER_UNIT_DIR}/openclaw-gateway.service"
COMPOSE_FILE="${COMPOSE_FILE:-/root/ReClaw-2.0/docker-compose.yml}"
COMPOSE_DIR="$(dirname "$COMPOSE_FILE")"
CANONICAL_NAME="openclaw-gateway"
PORT=18789
ENFORCE="${ENFORCE:-1}" # 1 = kill/remove duplicates; 0 = report only

log() { echo "[ensure-single-openclaw] $*"; }
warn() { echo "[ensure-single-openclaw][!] $*" >&2; }

log "canonical: docker compose service ${CANONICAL_NAME} (${COMPOSE_FILE})"

# --- 1) Disable host openclaw gateway install (user systemd) ---
if command -v systemctl >/dev/null 2>&1; then
  # Root user unit (common after `openclaw gateway install` as root)
  if systemctl --user --quiet is-active openclaw-gateway 2>/dev/null; then
    warn "Stopping rogue user systemd openclaw-gateway"
    systemctl --user stop openclaw-gateway 2>/dev/null || true
  fi
  if [[ -f "${USER_UNIT}" && ! -L "${USER_UNIT}" ]]; then
    warn "Disabling ${USER_UNIT}"
    mv -f "${USER_UNIT}" "${USER_UNIT}.disabled-by-reclaw.$(date +%s)" 2>/dev/null || true
    systemctl --user daemon-reload 2>/dev/null || true
  fi
  systemctl --user disable openclaw-gateway 2>/dev/null || true
  systemctl --user mask openclaw-gateway 2>/dev/null || true

  # Also mask system-level unit if someone installed one
  if systemctl list-unit-files openclaw-gateway.service 2>/dev/null | grep -q openclaw-gateway; then
    if systemctl is-active openclaw-gateway >/dev/null 2>&1; then
      warn "Stopping system openclaw-gateway.service"
      systemctl stop openclaw-gateway 2>/dev/null || true
    fi
    systemctl disable openclaw-gateway 2>/dev/null || true
    systemctl mask openclaw-gateway 2>/dev/null || true
  fi
fi

# --- 2) Only one Docker container named openclaw-gateway (remove extras) ---
# Any other container from openclaw image or name matching openclaw*gateway*
mapfile -t EXTRA_CONTAINERS < <(
  docker ps -aq --filter "name=openclaw" 2>/dev/null | while read -r id; do
    name=$(docker inspect -f '{{.Name}}' "$id" 2>/dev/null | sed 's#^/##')
    [[ "$name" == "$CANONICAL_NAME" ]] && continue
    # keep unrelated names? only kill clear gateway clones
    if [[ "$name" == *gateway* ]] || [[ "$name" == openclaw ]] || [[ "$name" == openclaw-cli* ]]; then
      echo "$id $name"
    fi
  done
)
if [[ ${#EXTRA_CONTAINERS[@]} -gt 0 ]]; then
  for row in "${EXTRA_CONTAINERS[@]}"; do
    id=${row%% *}
    name=${row#* }
    warn "Extra OpenClaw-related container: $name ($id)"
    if [[ "$ENFORCE" == "1" ]]; then
      warn "Removing $name"
      docker rm -f "$id" 2>/dev/null || true
    fi
  done
fi

# --- 3) Ensure compose gateway is Up ---
if ! docker compose -f "$COMPOSE_FILE" ps "$CANONICAL_NAME" 2>/dev/null | grep -qE 'Up|running'; then
  warn "Docker ${CANONICAL_NAME} is not Up — starting it"
  if [[ "$ENFORCE" == "1" ]]; then
    docker compose -f "$COMPOSE_FILE" up -d "$CANONICAL_NAME"
  else
    exit 1
  fi
fi

# Wait for container + port (recreate races used to fail the guard)
CANONICAL_CID=""
CANONICAL_PID=""
for attempt in $(seq 1 30); do
  CANONICAL_CID=$(docker compose -f "$COMPOSE_FILE" ps -q "$CANONICAL_NAME" 2>/dev/null | head -1)
  if [[ -n "$CANONICAL_CID" ]]; then
    state=$(docker inspect -f '{{.State.Status}}' "$CANONICAL_CID" 2>/dev/null || echo "")
    CANONICAL_PID=$(docker inspect -f '{{.State.Pid}}' "$CANONICAL_CID" 2>/dev/null || echo "")
    listeners=$(ss -tlnp 2>/dev/null | grep -E ":${PORT}\\s" || true)
    if [[ "$state" == "running" && -n "${listeners}" ]]; then
      break
    fi
  fi
  sleep 1
done
if [[ -z "$CANONICAL_CID" ]]; then
  warn "Could not resolve container id for ${CANONICAL_NAME}"
  exit 1
fi

# --- 4) Port 18789: at most one listener process tree ---
listeners=$(ss -tlnp 2>/dev/null | grep -E ":${PORT}\\s" || true)
if [[ -z "${listeners}" ]]; then
  warn "Nothing on :${PORT} after wait — try: docker compose -f ${COMPOSE_FILE} logs --tail=50 ${CANONICAL_NAME}"
  exit 1
fi

# Collect host PIDs holding the port
mapfile -t PORT_PIDS < <(echo "${listeners}" | grep -oE 'pid=[0-9]+' | sed 's/pid=//' | sort -u)
# Also collect process names
if [[ ${#PORT_PIDS[@]} -gt 1 ]]; then
  # IPv4+IPv6 docker-proxy is normal (two PIDs). Only act on true foreign listeners.
  foreign=0
  if [[ "$ENFORCE" == "1" ]]; then
    for pid in "${PORT_PIDS[@]}"; do
      # Keep anything in the docker container's process tree
      if [[ -n "$CANONICAL_PID" ]] && [[ "$pid" == "$CANONICAL_PID" ]]; then
        continue
      fi
      # Keep children of container init (node under tini)
      if [[ -n "$CANONICAL_PID" ]] && grep -q "^PPid:[[:space:]]*${CANONICAL_PID}$" "/proc/${pid}/status" 2>/dev/null; then
        continue
      fi
      # Walk up parents — if any ancestor is CANONICAL_PID, keep
      pp=$pid
      keep=0
      for _ in 1 2 3 4 5 6 7 8; do
        [[ -z "$pp" || "$pp" == "0" || "$pp" == "1" ]] && break
        if [[ -n "$CANONICAL_PID" && "$pp" == "$CANONICAL_PID" ]]; then
          keep=1
          break
        fi
        pp=$(awk '/^PPid:/{print $2}' "/proc/${pp}/status" 2>/dev/null || echo "")
      done
      if [[ "$keep" == "1" ]]; then
        continue
      fi
      cmd=$(tr '\0' ' ' <"/proc/${pid}/cmdline" 2>/dev/null || true)
      comm=$(cat "/proc/${pid}/comm" 2>/dev/null || true)
      # docker-proxy is REQUIRED for published ports (IPv4 + IPv6 = two PIDs). Never kill it.
      if [[ "$comm" == "docker-proxy" ]] || [[ "$cmd" == *"/docker-proxy"* ]] || [[ "$cmd" == *"docker-proxy"* ]]; then
        continue
      fi
      # tailscaled Tailscale Serve also binds :18789 on tailnet IP (HTTPS proxy to gateway).
      # Killing it drops remote Office/Control UI every guard cycle. Never kill it.
      if [[ "$comm" == "tailscaled" ]] || [[ "$cmd" == *"/usr/sbin/tailscaled"* ]] || [[ "$cmd" == *"tailscaled"* ]]; then
        continue
      fi
      # containerd / dockerd helpers
      if [[ "$comm" == "dockerd" || "$comm" == "containerd" || "$comm" == containerd-shim* ]]; then
        continue
      fi
      foreign=1
      warn "Killing non-canonical :${PORT} process pid=${pid} cmd=${cmd}"
      kill "$pid" 2>/dev/null || true
      sleep 0.5
      kill -9 "$pid" 2>/dev/null || true
    done
    if [[ "$foreign" == "1" ]]; then
      warn "Had foreign listeners on :${PORT} (removed). Current:"
      ss -tlnp 2>/dev/null | grep -E ":${PORT}\\s" || true
    fi
  else
    # report-only: ignore docker-proxy multiplicity
    for pid in "${PORT_PIDS[@]}"; do
      comm=$(cat "/proc/${pid}/comm" 2>/dev/null || true)
      cmd=$(tr '\0' ' ' <"/proc/${pid}/cmdline" 2>/dev/null || true)
      [[ "$comm" == "docker-proxy" || "$cmd" == *docker-proxy* ]] && continue
      [[ -n "$CANONICAL_PID" && "$pid" == "$CANONICAL_PID" ]] && continue
      foreign=1
    done
    if [[ "$foreign" == "1" ]]; then
      warn "MULTIPLE non-Docker PIDs on :${PORT}:"
      echo "${listeners}"
      exit 1
    fi
  fi
fi

# Host gateway processes NOT in our Docker cgroup.
# IMPORTANT: do not match shell wrappers whose *command text* merely mentions gateway
# (pgrep -f matches the full bash -c line and was killing agent sessions).
if [[ "$ENFORCE" == "1" && -n "$CANONICAL_CID" ]]; then
  # Whitelist every PID in the canonical container
  declare -A KEEP=()
  while read -r pid; do
    [[ -n "$pid" ]] && KEEP["$pid"]=1
  done < <(docker top "$CANONICAL_CID" -eo pid 2>/dev/null | awk 'NR>1 {print $1}')

  while read -r pid; do
    [[ -z "$pid" || ! -d "/proc/${pid}" ]] && continue
    [[ -n "${KEEP[$pid]:-}" ]] && continue
    if grep -q "$CANONICAL_CID" "/proc/${pid}/cgroup" 2>/dev/null; then
      continue
    fi
    # Only real node gateway executables (not bash/python wrappers that quote the string)
    comm=$(cat "/proc/${pid}/comm" 2>/dev/null || true)
    exe=$(readlink -f "/proc/${pid}/exe" 2>/dev/null || true)
    cmd=""
    if [[ -r "/proc/${pid}/cmdline" ]]; then
      cmd=$(tr '\0' ' ' <"/proc/${pid}/cmdline" 2>/dev/null || true)
    fi
    # Require node/tini binary + gateway args, not "bash -c ... gateway ..."
    if [[ "$comm" != "node" && "$comm" != "tini" && "$exe" != *"/node" && "$exe" != *"/tini" ]]; then
      continue
    fi
    case "$cmd" in
      *'dist/index.js gateway'*|*' openclaw gateway '*)
        warn "Killing non-Docker gateway pid=${pid} comm=${comm} exe=${exe}"
        kill "$pid" 2>/dev/null || true
        sleep 0.3
        kill -9 "$pid" 2>/dev/null || true
        ;;
    esac
  done < <(pgrep -x node 2>/dev/null; pgrep -x tini 2>/dev/null || true)
fi

# --- 5) Health ---
if ! curl -sf --max-time 5 "http://127.0.0.1:${PORT}/health" >/dev/null; then
  warn ":${PORT} /health failed"
  exit 1
fi

# Re-check single PID after kills (allow tini+node = parent/child both showing is OK if same tree)
listeners=$(ss -tlnp 2>/dev/null | grep -E ":${PORT}\\s" || true)
mapfile -t PORT_PIDS < <(echo "${listeners}" | grep -oE 'pid=[0-9]+' | sed 's/pid=//' | sort -u)
# If still multiple unrelated PIDs, fail
unrelated=0
for pid in "${PORT_PIDS[@]:-}"; do
  [[ -z "$pid" ]] && continue
  if grep -q "$CANONICAL_CID" "/proc/${pid}/cgroup" 2>/dev/null; then
    continue
  fi
  if [[ -n "$CANONICAL_PID" && "$pid" == "$CANONICAL_PID" ]]; then
    continue
  fi
  # child of container?
  pp=$(awk '/^PPid:/{print $2}' "/proc/${pid}/status" 2>/dev/null || echo "")
  if [[ -n "$CANONICAL_PID" && "$pp" == "$CANONICAL_PID" ]]; then
    continue
  fi
  # docker-proxy (IPv4/IPv6) is the published-port path for compose — not a second gateway
  comm=$(cat "/proc/${pid}/comm" 2>/dev/null || true)
  cmd=$(tr '\0' ' ' <"/proc/${pid}/cmdline" 2>/dev/null || true)
  if [[ "$comm" == "docker-proxy" ]] || [[ "$cmd" == *docker-proxy* ]]; then
    continue
  fi
  # Tailscale Serve listener on tailnet :18789 is not a second gateway
  if [[ "$comm" == "tailscaled" ]] || [[ "$cmd" == *tailscaled* ]]; then
    continue
  fi
  unrelated=$((unrelated + 1))
done
if [[ "$unrelated" -gt 0 ]]; then
  warn "Still have non-Docker listeners on :${PORT}:"
  echo "${listeners}"
  exit 1
fi

log "OK — single gateway healthy on 127.0.0.1:${PORT} (${CANONICAL_NAME} ${CANONICAL_CID:0:12})"
log "Tailscale Control UI: https://openclaw.tail20a090.ts.net"
log "Do NOT run: openclaw gateway install / openclaw gateway run on host"
log "Do NOT: docker run ... openclaw  (use: cd ${COMPOSE_DIR} && docker compose up -d openclaw-gateway)"
exit 0

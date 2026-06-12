#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/reclaw"
BACKUP_DIR="$REPO_DIR/openclaw-workspace-backup"
MEM_DIR="$HOME/.openclaw/workspace/memory"
BRANCH="ravenstack"
SAFE_MODEL="ollama/qwen3.5:4b"

echo "==> HARD RESET: Ollama + OpenClaw session state"

# 0) Restart Ollama cleanly
echo "==> Restarting Ollama"
sudo systemctl restart ollama
sleep 2
curl -fsS http://127.0.0.1:11434/api/tags >/dev/null && \
  echo "Ollama is up on 127.0.0.1:11434"

# 1) Save latest session memory (if any) into backup (you said you don't care, but it's cheap)
mkdir -p "$BACKUP_DIR"
if ls "$MEM_DIR"/*.md >/dev/null 2>&1; then
  LATEST_MEM="$(ls -t "$MEM_DIR"/*.md | head -n 1)"
  MEM_BASENAME="$(basename "$LATEST_MEM")"
  cp "$LATEST_MEM" "$BACKUP_DIR/$MEM_BASENAME"
  echo "Saved latest memory note to $BACKUP_DIR/$MEM_BASENAME"
else
  echo "No memory markdown files found in $MEM_DIR"
fi

# 2) Close the obviously cursed sessions if they exist
echo "==> Closing known sessions"
for key in \
  "agent:main:main" \
  "agent:main:dashboard:cb487d36-aace-478b-a402-30d139e73408"
do
  if openclaw sessions close "$key" >/dev/null 2>&1; then
    echo "Closed session: $key"
  else
    echo "No session to close: $key"
  fi
done

# 3) Force the model you want as default (your good one)
echo "==> Setting default model to $SAFE_MODEL"
openclaw models set "$SAFE_MODEL"

# 4) Restart gateway so everything is clean
echo "==> Restarting OpenClaw gateway"
openclaw gateway restart >/dev/null 2>&1 || true
sleep 2
openclaw gateway status

# 5) Optionally commit backup note (silent if nothing changed)
if git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  if ls "$MEM_DIR"/*.md >/dev/null 2>&1; then
    LATEST_MEM="$(ls -t "$MEM_DIR"/*.md | head -n 1)"
    MEM_BASENAME="$(basename "$LATEST_MEM")"
    cd "$REPO_DIR"
    git add "$BACKUP_DIR/$MEM_BASENAME" 2>/dev/null || true
    if ! git diff --cached --quiet; then
      git commit -m "checkpoint: auto-save OpenClaw memory before reset" || true
      git pull --rebase origin "$BRANCH" || true
      git push origin "$BRANCH" || true
      echo "Backup note committed and pushed to $BRANCH"
    fi
  fi
fi

echo
echo "==> DONE."
echo "Now:"
echo "  1) Open a BRAND NEW OpenClaw chat (not the old one)"
echo "  2) Send:  say \"pong\" and nothing else"

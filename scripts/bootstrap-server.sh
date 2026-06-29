#!/bin/bash
# =============================================================================
# bootstrap-server.sh — Hetzner Fresh Server Setup
# Run as root immediately after Hetzner OS rebuild
# Ubuntu 24.04 | OpenClaw + ReClaw + Tailscale + Docker + Llama.cpp Brain
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
fail() { echo -e "${RED}[\u2717]${NC} $1"; exit 1; }

# =============================================================================
# CONFIG — fill these in before running — NEVER commit with values set
# =============================================================================
OPENCLAW_PASSWORD=""       # Fill in before running
TAILSCALE_AUTHKEY=""       # From https://login.tailscale.com/admin/settings/keys
GITHUB_USER="jasandroidx"
RECLAW_REPO="ReClaw-2.0"
HOSTNAME_SET="openclaw"

[[ -z "$OPENCLAW_PASSWORD" ]] && fail "Set OPENCLAW_PASSWORD at the top of this script first!"
[[ -z "$TAILSCALE_AUTHKEY" ]] && fail "Set TAILSCALE_AUTHKEY at the top of this script first!"

# =============================================================================
# STEP 1 — System baseline
# =============================================================================
log "Setting hostname + updating system"
hostnamectl set-hostname "$HOSTNAME_SET"
apt-get update -qq && apt-get upgrade -y -qq
apt-get install -y -qq \
  curl wget git vim htop unzip ufw fail2ban \
  build-essential ca-certificates gnupg lsb-release \
  python3 python3-pip python3-venv jq cmake

# =============================================================================
# STEP 2 — Swap (4GB)
# =============================================================================
if [[ ! -f /swapfile ]]; then
  log "Creating 4GB swapfile"
  fallocate -l 4G /swapfile && chmod 600 /swapfile
  mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
else
  warn "Swapfile already exists, skipping"
fi

# =============================================================================
# STEP 3 — Docker
# =============================================================================
log "Installing Docker"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -qq
apt-get install -y -qq \
  docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
log "Docker $(docker --version) installed"

# =============================================================================
# STEP 4 — Tailscale
# =============================================================================
log "Installing Tailscale"
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="$HOSTNAME_SET" --accept-routes
log "Tailscale IP: $(tailscale ip -4)"

# =============================================================================
# STEP 5 — Firewall (UFW)
# =============================================================================
log "Configuring firewall"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp                                 # SSH
ufw allow 8000/tcp                               # ReClaw API
ufw allow in on tailscale0 to any port 18789     # OpenClaw gateway (Tailscale only)
ufw allow in on tailscale0 to any port 18790     # OpenClaw bridge (Tailscale only)
ufw --force enable
log "Firewall active (Local AI port 8080 remains internal-only)"

# =============================================================================
# STEP 6 — Clone ReClaw-2.0
# =============================================================================
log "Cloning ReClaw-2.0"
cd /root
if [[ -d ReClaw-2.0 ]]; then
  warn "ReClaw-2.0 already exists, pulling latest"
  cd ReClaw-2.0 && git pull
else
  git clone "https://github.com/$GITHUB_USER/$RECLAW_REPO.git"
  cd ReClaw-2.0
fi
if [[ ! -f .env ]]; then
  cp .env.example .env
  warn "Created .env from .env.example — edit /root/ReClaw-2.0/.env with your API keys!"
fi

# =============================================================================
# STEP 7 — ReClaw Docker build + start
# =============================================================================
log "Building and starting ReClaw API"
docker compose build --no-cache
docker compose up -d
log "ReClaw API starting on port 8000"

# =============================================================================
# STEP 8 — OpenClaw (pre-built ghcr image — avoids Docker Hub timeouts)
# =============================================================================
log "Setting up OpenClaw"
mkdir -p /root/.openclaw

cat > /root/.openclaw/openclaw.json << EOF
{
  "mode": "local",
  "auth": {
    "allowTailscale": true,
    "token": null,
    "mode": "password",
    "password": "$OPENCLAW_PASSWORD"
  },
  "bind": "loopback"
}
EOF
log "openclaw.json written (clean config)"

if [[ ! -d /root/openclaw ]]; then
  git clone https://github.com/OpenClaw/openclaw.git /root/openclaw || \
    warn "OpenClaw repo clone failed — may need a GitHub token"
fi
cd /root/openclaw

cat > .env << 'ENVEOF'
OPENCLAW_IMAGE=ghcr.io/openclaw/openclaw:latest
ENVEOF

log "Pulling OpenClaw image from ghcr.io"
docker pull ghcr.io/openclaw/openclaw:latest
docker rm -f boyd-bot-claw 2>/dev/null || true
docker compose up -d

# =============================================================================
# STEP 9 — Build Local AI Brain (llama.cpp + Qwen-2.5-Coder)
# NOTE: This step runs last so a failure doesn't abort Docker setup above.
#       Compile uses -j 4 (not -j 8) to avoid OOM on 8GB RAM server.
#       Model download is ~4.5GB — expect 10-20 min on first run.
# =============================================================================
log "Cloning llama.cpp"
cd /root
if [[ -d llama.cpp ]]; then
  warn "llama.cpp already exists, pulling latest"
  cd llama.cpp && git pull
else
  git clone https://github.com/ggerganov/llama.cpp.git
  cd llama.cpp
fi

log "Compiling llama.cpp (this takes ~10-15 min, using -j 4 to protect RAM)"
cmake -B build -DCMAKE_BUILD_TYPE=Release && \
  cmake --build build --config Release -j 4 || \
  { warn "llama.cpp build failed — skipping local AI brain setup"; exit 0; }

mkdir -p /root/models
if [[ ! -f /root/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf ]]; then
  log "Downloading Qwen-2.5-Coder-7B-Instruct (~4.5GB, this will take a while...)"
  wget -q --show-progress -O /root/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
    "https://huggingface.co/bartowski/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf"
else
  log "Model file already exists, skipping download"
fi

log "Creating llama-brain systemd service"
cat > /etc/systemd/system/llama-brain.service << 'SVCEOF'
[Unit]
Description=Llama.cpp Local AI Brain Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/llama.cpp
ExecStart=/root/llama.cpp/build/bin/llama-server \
  -m /root/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
  -c 4096 \
  --threads 8 \
  --host 127.0.0.1 \
  --port 8080
Restart=always
RestartSec=5
Nice=-10

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable --now llama-brain
log "Local AI brain service started on 127.0.0.1:8080"

# =============================================================================
# STEP 10 — Final status check
# =============================================================================
log "Waiting 15s for containers to stabilize..."
sleep 15

echo ""
echo "============================================================"
echo "  BOOTSTRAP COMPLETE — STATUS"
echo "============================================================"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "Tailscale IP: $(tailscale ip -4 2>/dev/null || echo 'run: tailscale ip -4')"
echo "Local AI Brain: $(systemctl is-active llama-brain) on 127.0.0.1:8080"
echo ""
warn "NEXT STEPS:"
echo "  1. Edit /root/ReClaw-2.0/.env with your API keys"
echo "  2. To use local AI: set OpenAI base URL to http://127.0.0.1:8080/v1"
echo "  3. OpenClaw via Tailscale: http://$(tailscale ip -4 2>/dev/null):18789"
echo "  4. Or SSH tunnel: ssh -L 18789:localhost:18789 root@<server-ip>"
echo "     then open http://localhost:18789"
echo "  5. Check logs: docker logs openclaw-openclaw-gateway-1"
echo "============================================================"

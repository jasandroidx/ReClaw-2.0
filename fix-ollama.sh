#!/bin/bash
# fix-ollama.sh — one-shot Ollama + ReClaw stack repair
# Run: chmod +x fix-ollama.sh && sudo ./fix-ollama.sh

set -e
echo "==> [1/4] Patching Ollama to listen on all interfaces..."
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf <<EOF
[Service]
Environment=OLLAMA_HOST=0.0.0.0:11434
EOF

echo "==> [2/4] Reloading systemd and restarting Ollama..."
systemctl daemon-reload
systemctl restart ollama
sleep 4

echo "==> [3/4] Testing Ollama on host gateway..."
curl -sf http://172.17.0.1:11434/api/version && echo "" && echo "✅ Ollama is UP" || { echo "❌ Ollama still not reachable — check: systemctl status ollama"; exit 1; }

echo "==> [4/4] Restarting ReClaw stack..."
cd /opt/reclaw
docker compose down
docker compose up -d --build

echo ""
echo "✅ Done. Open your dashboard: http://$(hostname -I | awk '{print $1}'):8080"
echo "   You should see ● ON in green at the top."

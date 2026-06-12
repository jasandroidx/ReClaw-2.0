#!/bin/bash
echo "Opening ReClaw Pixel Sim Tool (RPG Ops Floor)..."
echo "Main dashboard: http://localhost:8085"
echo "Pixel Sim: http://localhost:8085/pixel-sim.html"
echo "Remote/Tailscale: http://$(tailscale ip -4 2>/dev/null || echo 'your-tailscale-ip'):8085/pixel-sim.html"
if command -v xdg-open >/dev/null; then
  xdg-open "http://localhost:8085/pixel-sim.html"
elif command -v python3 >/dev/null; then
  python3 -m webbrowser "http://localhost:8085/pixel-sim.html" 2>/dev/null || echo "Open the URL in your browser."
else
  echo "Open the URL above in your browser."
fi

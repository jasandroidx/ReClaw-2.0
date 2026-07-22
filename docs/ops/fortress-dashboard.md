# Ravenstack Fortress dashboard (ops)

## Live
- URL (Tailscale): http://100.108.130.82:3000
- systemd: `ravenstack-fortress.service`
- WorkingDirectory: `/root/ravenstack-fortress/dashboard`
- UFW: TCP 3000 on `tailscale0` only

## Commands
```bash
systemctl status ravenstack-fortress
systemctl restart ravenstack-fortress
journalctl -u ravenstack-fortress -n 50 --no-pager
curl -s http://127.0.0.1:8000/fortress-state | head
```

## Rules
- This service is **UI only**. OpenClaw gateway stays Docker-only:
  `cd /root/ReClaw-2.0 && docker compose up -d openclaw-gateway`
- Never `openclaw gateway run` on host.

## Login
- Gateway URL: `ws://100.108.130.82:3000/gateway-ws`
- Token: OPENCLAW_GATEWAY_TOKEN from ReClaw `.env` / login form

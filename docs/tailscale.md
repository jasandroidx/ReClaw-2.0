# tailscale.md — ReClaw 2.0 + Tailscale (Clean Remote Access)

Tailscale is the primary way you (and the Discord bot / future visual frontend later) talk to the Hetzner ReClaw 2.0 Gateway. It provides secure access to the general platform and domain outputs (e.g. Obsidian Rural Data packages).

This follows the exact pattern used in the official OpenClaw gateway onboarding (127.0.0.1 binding + `tailscale serve`). The previous networking update to allow Tailscale IP access is compatible when using host-level serve.

## Why Tailscale
- Zero public ports.
- Works great on rural internet (both ends).
- Gives you a stable magic DNS name (yourbox.tailnet.ts.net).
- Easy to add your phone, laptop, future mini PCs in the shop, etc.
- `tailscale serve` lets you expose the Gateway with Tailscale authentication (no extra reverse proxy tokens at first).

## Setup on Hetzner (Production Box)

```bash
# 1. Install
curl -fsSL https://tailscale.com/install.sh | sh

# 2. Bring it up (use your tailnet login key or interactive)
sudo tailscale up --ssh   # --ssh is nice for later direct access

# 3. Confirm
tailscale ip -4
tailscale status
```

## Hardened Tailscale Exposure (current production on Openclaw box)

**OpenClaw gateway (Docker compose only, host network) — dual path:**

| Path | Role | URL |
|------|------|-----|
| **PRIMARY** | Tailscale Serve (HTTPS/WSS MagicDNS) | **`wss://openclaw.tail20a090.ts.net`** |
| **FALLBACK** | Direct bind `lan` on tailnet IP | `ws://100.108.130.82:18789` (debug / non-mobile) |
| Control UI | Serve | `https://openclaw.tail20a090.ts.net/` |
| Health | loopback / Serve | `http://127.0.0.1:18789/health` · `https://openclaw.tail20a090.ts.net/health` |
| ReClaw API | Serve path | `https://openclaw.tail20a090.ts.net/reclaw/health` |

Config (`~/.openclaw/openclaw.json`):
- `gateway.bind: lan` — listens `0.0.0.0:18789` (includes loopback for Serve + Tailscale IP fallback)
- `gateway.controlUi.allowedOrigins` — must include **`https://localhost`** (Android okhttp over wss) and MagicDNS
- `gateway.trustedProxies: ["127.0.0.1","::1"]` — Tailscale Serve proxy headers
- Host multi-path Serve via `scripts/ensure-tailscale-mcp-funnel.sh` (not in-container serve — permission)

Stable URL SOT: `data/openclaw_android_url.txt` (rewritten by ensure script).

### PDANet USB tethering (common timeout cause)

PDANet / USB tethering rewrites routes on the **phone and/or tethered PC** and breaks Tailscale (timeouts, DERP-only, wrong egress). It does **not** mean the Hetzner gateway is down.

**When pairing Android:**
1. **Disconnect PDANet USB tether** (stop USB tethering / PDANet share).
2. Phone on **cellular or normal Wi‑Fi** with **Tailscale connected**.
3. Server URL on phone: **`wss://openclaw.tail20a090.ts.net`** only (never public IP, never stale `100.119.x.x`).
4. Paste gateway token; if “pairing required”, approve from Control UI or `openclaw devices list`.

**Why timeouts looked like “gateway down”:** Serve + health can be live on the server while the phone’s Tailscale path is broken by tether.

```bash
# Ensure Tailscale is active
tailscale status
tailscale ip -4   # must be 100.108.130.82 on this host

# Gateway (Docker only — never host systemd openclaw)
cd /root/ReClaw-2.0
docker compose up -d openclaw-gateway
bash scripts/ensure-tailscale-mcp-funnel.sh
bash scripts/ensure-single-openclaw.sh
bash scripts/verify-openclaw-android-path.sh
```

Test from this box or any Tailscale peer:
```bash
curl -sf http://127.0.0.1:18789/health
curl -sf http://100.108.130.82:18789/health          # lan fallback
curl -sfk https://openclaw.tail20a090.ts.net/health  # Serve primary
curl -sfk https://openclaw.tail20a090.ts.net/reclaw/health
tailscale ping -c 2 galaxy-a15-5g
```

**Hardening notes** (reflected in updated docker-compose.yml + SETUP.md):
- Docker logging driver with rotation (no unbounded growth)
- Container ulimits + resource limits
- All session activity logged to disk (`data/sessions/*/logs/`) — survives restarts
- Vault mount (`/root/obsidian_vault`) is the durable long-term memory
- No public ports; all access authenticated by Tailscale

This is the clean, cheap, reliable pattern. For full boot persistence, wrap the `tailscale serve` in a systemd service (`reclaw-tailscale-serve.service`). See SETUP.md for full deploy checklist.

## On Your Local Dev PC (Windows)

Install Tailscale, join the same tailnet.

Now your local scripts or the future Discord bot running on your PC can hit the Hetzner Gateway over the tailnet as if it were local.

For Obsidian output:
- Option A (simplest for start): On Hetzner, point OBSIDIAN_VAULT_PATH to a directory that you rsync or git-clone into your local vault.
- Option B: Run a lightweight Syncthing or Tailscale + shared folder between the two machines for the "Rural Data" subfolder.
- Option C (future): Make the ObsidianWriter also push a git commit to a private repo that your vault watches.

## SSH Fallback (when Tailscale is down or for initial bootstrap)

You can still just:

```bash
ssh user@hetzner-ip   # if you have key or password
# or even better over Tailscale once it's up:
ssh user@100.x.x.x     # the Tailscale IP
cd /opt/reclaw
docker compose logs -f
```

## Security Notes Specific to Tailscale + Gateway

- The `tailscale serve` token is powerful — treat it like an API key.
- You can later add `tailscale serve --auth` or Funnel with additional checks.
- In the Gateway code we will add a simple `Authorization: Bearer $RECLAW_GATEWAY_TOKEN` check that is separate from Tailscale (belt + suspenders).
- All approval decisions ("who granted live_fetch") should be done by a human on a Tailscale-authenticated device, or by a bot that itself authenticates via Tailscale + a short-lived token.

## Quick Test from Another Tailscale Device

```bash
curl -v https://<your-reclaw-ts-net>/health
```

If you get the JSON back, the control plane is reachable cleanly and securely.

This is the same pattern the parent OpenClaw uses for its gateway on Hetzner. ReClaw re-uses it so the whole rural operation (data swarm + future business automation agents) speaks the same access language.

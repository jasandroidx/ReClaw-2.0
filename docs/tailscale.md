# tailscale.md — ReClaw 2.0 + Tailscale (Clean Remote Access)

Tailscale is the primary way you (and the Discord bot later) talk to the Hetzner ReClaw Gateway and get the Obsidian packages back to your local vault.

This follows the exact pattern used in the official OpenClaw gateway onboarding.

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

## Expose the ReClaw Gateway (the OpenClaw way)

The Gateway container only listens on 127.0.0.1:8000 inside the box (see docker-compose).

On the Hetzner host:

```bash
# Serve it over Tailscale (background)
tailscale serve --bg http://127.0.0.1:8000

# Check what URL + token you got
tailscale serve status
```

You will get something like:
https://reclaw-box-XXXX.ts.net

And a token you can put in openclaw-style configs or just use the HTTPS URL + Tailscale identity.

From any device on the same tailnet you can now:

```bash
curl https://reclaw-box-XXXX.ts.net/health
curl -X POST "https://reclaw-box-XXXX.ts.net/trigger/Pike?auto_approve=true"
```

No port forwarding, no Cloudflare tunnel, no nginx config (yet).

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

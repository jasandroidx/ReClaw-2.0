# Named Cloudflare tunnel for ReClaw MCP

## Why

Quick tunnels (`*.trycloudflare.com`) **rotate hostnames** on restart and have **no auth**.  
A **named tunnel** on your domain stays stable for SuperGrok Custom Connectors.

## Prerequisites

1. Cloudflare account + a zone you control  
2. `cloudflared` installed on this host (already present)  
3. One-time browser login:

```bash
cloudflared tunnel login
```

## Setup

```bash
export MCP_TUNNEL_NAME=reclaw-mcp
export MCP_TUNNEL_HOSTNAME=mcp.YOURDOMAIN.com   # must be on Cloudflare DNS
bash /root/ReClaw-2.0/scripts/setup-named-mcp-tunnel.sh
```

Then update SuperGrok connector URL to `https://mcp.YOURDOMAIN.com/mcp`.

## Optional Access (auth)

In Cloudflare Zero Trust → Access:

1. Application for `mcp.YOURDOMAIN.com`  
2. Policy: allow your email only  
3. Or use [MCP managed OAuth](https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/) when ready  

Until Access is on, treat the URL as a secret (same as quick tunnel).

## Fallback

Quick tunnel remains: `scripts/run-mcp-public-tunnel.sh` + `reclaw-mcp-tunnel.service` (current default).  
Tailscale always preferred for private ops: `https://openclaw.tail20a090.ts.net:8100/mcp`.

## Verify

```bash
cat /root/ReClaw-2.0/data/mcp_public_url.txt
curl -sf https://mcp.YOURDOMAIN.com/health
systemctl status reclaw-mcp-tunnel
```

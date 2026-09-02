---
title: MCP URLs — who uses what (SOT cheat sheet)
type: ops-sot
status: active
date: 2026-08-13
aliases: [mcp url, connector url, funnel, public mcp, claude connector, super grok mcp]
---

# MCP URLs — who uses what

**If you only remember one public link, use this:**

```text
https://openclaw.tail20a090.ts.net/rk7m2q9x/mcp
```

Health: `https://openclaw.tail20a090.ts.net/rk7m2q9x/health` → expect **200**  
GET `/mcp` → expect **406** (normal for streamable-http; clients use POST/session)

**SOT files on server:**  
`/root/ReClaw-2.0/data/mcp_public_url.txt` · `data/MCP_PUBLIC_PLANE.txt`  
Full map: [[mcp-connector]] · Repo: `docs/MCP_CONNECTOR.md`

---

## Client → URL (copy-paste)

| Who | URL | Why |
|-----|-----|-----|
| **Claude** Custom Connector | `https://openclaw.tail20a090.ts.net/rk7m2q9x/mcp` | Public Funnel **:443** + secret path (Anthropic needs 443, not :10000) |
| **Super Grok / grok.com** | **same** | Same public Funnel URL |
| **Perplexity** (remote MCP) | **same** | Same public Funnel URL |
| **Any cloud AI** off-tailnet | **same** | One public SOT — do not invent per-product URLs |
| **OpenClaw gateway** (Docker on openclaw host) | `https://openclaw.tail20a090.ts.net:8100/mcp` | Tailnet **Serve** HTTPS — gateway cannot reliably hairpin Funnel |
| **You / agents on Tailscale** | Serve `:8100` **or** Funnel above | Either works on tailnet; Serve is fine for local ops |
| **Grok Build stdio** on server | no URL — `reclaw-platform` stdio | Process-local |
| **Keep MCP** | `https://openclaw.tail20a090.ts.net:8110/mcp` | Separate service (Serve → host :8111) |

---

## Never use

| Bad | Why |
|-----|-----|
| `http://100.108.130.82:8100/...` | Serve is **HTTPS** → “Client sent HTTP to HTTPS server” |
| `*.trycloudflare.com/mcp` | Quick tunnels **rotate**; unit disabled on purpose |
| `…:10000/rk7m2q9x/mcp` | Old Funnel port; Claude won’t dial non-443 reliably |
| Funnel root `https://openclaw…ts.net/` or `/mcp` | **Not** published — only secret path `/rk7m2q9x` |

---

## Architecture (one line)

```text
Cloud clients → Funnel :443 /rk7m2q9x → http://127.0.0.1:8100 (bridge)
Gateway/Docker → Serve :8100 HTTPS → same bridge
```

---

## Operator checklist

1. Cloud product connector broken? → paste **public Funnel URL** above; delete stale CF/:10000 entries.  
2. Gateway `bundle-mcp` / HTTPS errors? → openclaw.json must use **Serve :8100**, not raw IP HTTP.  
3. After Funnel change: re-read `data/mcp_public_url.txt`; run `scripts/ensure-tailscale-mcp-funnel.sh` if needed.  
4. Do **not** re-enable `reclaw-mcp-tunnel` (quick tunnel) without a named fixed host.

**Last verified:** 2026-08-13 — Funnel :443 path live; GET /mcp → 406; health → 200.

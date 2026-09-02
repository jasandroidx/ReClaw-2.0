# FOR CLAUDE — read this before you touch the fortress

Jason told you to open this file. Treat it as law for this host.

You (Claude Code) caused a production outage at **01:15 UTC 2026-08-18**. You wrote `tools/raven_bridge_server.py` and `raven-mcp-bridge.service`, aimed it at port **8100** because Funnel already uses that port, ran `ss` + `curl /sse`, got 404 (the real server is streamable-http on `/mcp`), then `fuser -k 8100` / `kill -9` the real `reclaw-mcp-bridge` PID so your new SSE server could bind.

That is forbidden.

Also read, in order:

1. `/root/obsidian_vault/Ravenstack/wiki/hot.md`
2. `/root/obsidian_vault/Ravenstack/ops/SESSION-START.md`
3. `/root/obsidian_vault/Ravenstack/ops/incidents/INDEX.md`

## Hard rules — do not violate

1. **Port `127.0.0.1:8100` is reclaw-platform only** (systemd `reclaw-mcp-bridge` → `scripts/run-reclaw-mcp-bridge.sh`). Do not bind anything else there. Do not enable `raven-mcp-bridge` (it is **masked**). Do not run `tools/raven_bridge_server.py`.
2. **If :8100 is occupied, STOP.** Identify the process. If it is reclaw-platform, leave it. Never `fuser -k` / kill the pid on 8100.
3. **Keep MCP is :8111.** New MCP tools go into reclaw-platform or a new port Jason approves — never a second server on 8100.
4. **Before mutating gateway / MCP / Docker / Tailscale**, grep `ops/incidents/INDEX.md` for the symptom. After a real fix, add a card there. That is the one incident log.
5. **Single OpenClaw gateway:** Docker compose service `openclaw-gateway` only. County queue stays frozen.

If Jason asks you to diagnose or fix the stack: sitrep first, incidents INDEX second, mutate least. Do not invent a parallel MCP, systemd unit, or “RavenKeep bridge.”

# OpenClaw Mechanic — runbooks (Hetzner Fortress)

Exact commands. Prefer these over inventing.

## Single gateway

```bash
cd /root/ReClaw-2.0
docker compose ps openclaw-gateway
docker compose up -d openclaw-gateway
docker compose restart openclaw-gateway
bash scripts/ensure-single-openclaw.sh
```

**Forbidden:** `openclaw gateway install|run|start` on host; second `docker run` openclaw.

## OpenClaw CLI (version-safe)

```bash
docker exec openclaw-gateway openclaw <cmd>
# Host CLI may be older than config (2026.7.x) — avoid for config writes when possible
```

## Devices / nodes

```bash
docker exec openclaw-gateway openclaw devices list
docker exec openclaw-gateway openclaw devices approve <requestId>
docker exec openclaw-gateway openclaw nodes approve <requestId>
```

## Models / auth (no key printing)

```bash
docker exec openclaw-gateway openclaw models status
docker exec openclaw-gateway openclaw models set <provider/model>
docker exec openclaw-gateway openclaw models fallbacks list
# Paste key from env already in container — never echo:
docker exec -i openclaw-gateway sh -c \
  'printf "%s" "$OPENROUTER_API_KEY" | openclaw models auth paste-api-key --provider openrouter --profile-id openrouter:default'
```

Do **not** hardcode primary models in skills; always read live status.

## Config ownership

```bash
# After root edit of openclaw.json:
chown 1000:1000 /root/.openclaw/openclaw.json
chmod 600 /root/.openclaw/openclaw.json
docker exec openclaw-gateway openclaw config validate
```

Backup first:

```bash
cp -a /root/.openclaw/openclaw.json \
  "/root/.openclaw/openclaw.json.bak-$(date -u +%Y%m%dT%H%M%SZ)"
```

## MCP

```bash
systemctl is-active reclaw-mcp-bridge reclaw-mcp-tunnel
curl -sf http://127.0.0.1:8100/health
cat /root/ReClaw-2.0/data/mcp_public_url.txt   # public grok.com connector (rotates)
# Tailscale MCP: https://openclaw.tail20a090.ts.net:8100/mcp
systemctl restart reclaw-mcp-tunnel   # if public dead; then re-read URL file
```

OpenClaw agent MCP: `mcp.servers.reclaw-platform.enabled` should be true for Raziel sitrep tools.

## Health / sitrep

Prefer MCP: `reclaw-platform__project_sitrep` · `stack_health` · `docker_status` · `openclaw_health` · `connector_status`

Shell fallback:

```bash
cd /root/ReClaw-2.0
./scripts/post-deploy-healthcheck.sh
docker compose ps
tailscale status | head
```

## Ports (typical)

| Service | Port |
|---------|------|
| ReClaw API | 8000 |
| OpenClaw gateway | 18789 |
| Fortress dashboard | 8081 |
| MCP bridge | 8100 |
| Ollama | 11434 |
| Permanent outbox | 8765 on Tailscale IP |

## Outbox delivery

```bash
# Write file for Jason
cp artifact /root/outbox/NAME.html
# Tell him: http://100.108.130.82:8765/NAME.html
# Landing: http://100.108.130.82:8765/
```

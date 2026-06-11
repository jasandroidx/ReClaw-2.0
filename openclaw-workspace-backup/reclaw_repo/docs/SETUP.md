# SETUP.md — ReClaw 2.0 Platform (Local Dev + Hetzner Production)

## 1. Clone & Environment (both places)

```bash
git clone <your-reclaw-repo> reclaw
cd reclaw
cp .env.example .env
# edit .env — most important: OBSIDIAN_VAULT_PATH
```

On **local Windows dev mirror** (your PC):
```
OBSIDIAN_VAULT_PATH=C:/Users/Jason/Desktop/Obsidian Claw
OBSIDIAN_SUBDIR=Rural Data
USE_LIVE_FETCH=false   # keep false until you trust the scrapers
```

On **Hetzner** (Linux):
```
OBSIDIAN_VAULT_PATH=/data/obsidian-exports   # or wherever you want the .md to land
# You will later rsync / git / Syncthing this folder into your real Obsidian vault on the Windows side, or mount it.
```

## 2. Python Local Run (fastest for dev)

```bash
python -m venv .venv
. .venv/bin/activate   # or on Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Quick test with full pipeline + Obsidian write (uses seeds, safe)
python -m reclaw.cli run --county Pike --area Winslow

# Or via the Gateway sync endpoint (also creates full session + approvals log)
python -c "
from api.main import run_sync
print(run_sync(county='Pike', area='Winslow', auto_approve=False))
"
```

The markdown (from the initial rural_data module) will appear in your vault under the Rural Data subfolder.

## 3. Docker (local test of prod image)

```bash
docker compose build
docker compose up -d
curl http://localhost:8000/health
curl -X POST "http://localhost:8000/run-sync?county=Pike&area=Winslow&auto_approve=false"
```

Check `data/sessions/` and your Obsidian folder.

## 4. Hetzner Production Deploy (Hardened)

Current state on this Openclaw box (/opt/reclaw):

1. Ensure host prep (one-time):
   - `sudo chown -R 1000:1000 /root/obsidian_vault /opt/reclaw/data /opt/reclaw/outputs` (matches container user)
   - Tailscale running + `tailscale serve --bg http://127.0.0.1:8000` (or as systemd unit `reclaw-tailscale-serve`)

2. Deploy (safe, no data loss):
   ```bash
   cd /opt/reclaw
   docker compose config                  # validate changes
   docker compose down --remove-orphans   # stops cleanly
   docker compose up -d --build
   docker compose ps
   curl -f http://127.0.0.1:8000/health   # should return {"status": "ok", ...}
   ```

3. Logs (new hardening):
   - Container: `docker compose logs --tail=100 reclaw-api` or `journalctl -u docker --since "10 min ago"`
   - Session audit: `data/sessions/<id>/logs/session.log` and `security.log` (disk truth, survives restarts)
   - Rotation: Docker json-file (10m max, 3 files) prevents unbounded growth.

Cron example (host level, seeds-first):
```bash
0 8 * * * cd /opt/reclaw && docker compose exec -T reclaw-api python -m reclaw.cli run --county Pike --area Winslow --dry >> /var/log/reclaw-daily.log 2>&1
```

This keeps everything simple, cheap, and reliable. Obsidian vault at `/root/obsidian_vault` is the long-term memory.

## 5. Tailscale (Primary Remote Access — Recommended)

See docs/tailscale.md for the exact steps that match the official OpenClaw gateway + Tailscale serve pattern.

Short version:
- Install Tailscale on Hetzner and on your local machines.
- On Hetzner: `tailscale up`
- Gateway binds to 127.0.0.1:8000 only.
- Use `tailscale serve --bg http://127.0.0.1:8000` (or the Funnel variant if you want a public-but-Tailscale-auth URL).
- All access to the API and to the Obsidian export folder happens over the Tailscale mesh.
- No open ports to the scary internet.

SSH fallback: just `ssh user@hetzner` (still over Tailscale or WireGuard) and `docker compose logs -f reclaw-api`.

## 6. First Real Data Run + Obsidian

After a successful Pike/Winslow run you should see in your Obsidian vault:

```
Rural Data/
  2026-06-04-pike-winslow.md
  2026-06-04-pike-winslow.json   (sidecar, Dataview/Bases friendly)
  _latest.md
```

Open the .md (from rural_data module). It contains frontmatter + the exact sections needed for content/channel use (Key Stats, Red Flags, Content Angles, full provenance). Future domains will have analogous structured output.

## 7. Adding a New County Seed

1. Create `data/seeds/<county_lowercase>_<area>_2025.json` modeled after the Pike one.
2. Update Researcher to have a small loader that prefers the seed file for that county when live is off.
3. Add a test in examples/ or tests/.

## 8. Cron / Daily Radar for the Channel

On Hetzner (inside the container or host):

```cron
0 7 * * * docker exec reclaw-api python -c "
from api.main import run_sync
run_sync('Pike', 'Winslow', auto_approve=True)
run_sync('Gibson', 'Oakland City', auto_approve=True)
" >> /var/log/reclaw-daily.log 2>&1
```

Then the new .md files just appear in Obsidian on next sync.

## 9. Verifying a Run End-to-End (Checklist)

- [ ] `data/runs/` has a new timestamped .json with full ContentPackage
- [ ] `data/sessions/<new-session>/` exists with soul/, handoffs/, approvals/granted/, logs/
- [ ] The Obsidian .md exists and has frontmatter with the package id + risk score
- [ ] No live network calls happened unless you explicitly approved
- [ ] `cat data/sessions/.../logs/session.log` shows SOULs loaded and gates checked

This setup is intentionally small. It will grow cleanly when we add Scriptwriter and the business-services agents.

# Upwork job scanner

Scan Upwork on a schedule, rank jobs you care about, write a digest. **Never auto-applies.**

## Files

| Path | Role |
|------|------|
| `data/upwork_preferences.yaml` | **Edit this** — keywords, budget floors, excludes |
| `tools/upwork_scan.py` | Scanner |
| `data/upwork_digests/YYYY-MM-DD.md` | Digests |
| `data/cache/upwork/seen_jobs.json` | Dedupe |
| `Ravenstack/ops/upwork-digest-latest.md` | Vault copy of latest |
| `agents/upwork_watcher/SOUL.md` | Agent contract |
| `reclaw-upwork-scan.timer` | Every ~2 days at 14:00 UTC |

## Quick start

```bash
cd /root/ReClaw-2.0

# 1. Edit prefs (queries, must/exclude, $ floors)
nano data/upwork_preferences.yaml

# 2. Dry run with demo jobs (no Upwork account needed)
PYTHONPATH=. .venv/bin/python tools/upwork_scan.py --demo --dry-run

# 3. Real run (demo until token set)
PYTHONPATH=. .venv/bin/python tools/upwork_scan.py
```

## Live Upwork data (recommended)

Upwork killed public RSS. Live search needs their **GraphQL API** + your OAuth token.

1. Create an app: https://www.upwork.com/developer/  
2. Complete OAuth; put bearer token in `.env`:

```bash
UPWORK_ACCESS_TOKEN=your_token_here
```

3. Re-run:

```bash
PYTHONPATH=. .venv/bin/python tools/upwork_scan.py
```

GraphQL field names change; if the query 400s, check Upwork docs and adjust `fetch_graphql` in `tools/upwork_scan.py`. Scoring and digests stay the same.

### Import path (no API yet)

Export/save jobs as JSON list:

```json
[
  {
    "id": "abc",
    "title": "Build Python agent pipeline",
    "description": "...",
    "url": "https://www.upwork.com/jobs/...",
    "budget_type": "hourly",
    "budget_min": 40,
    "budget_max": 70,
    "experience": "expert",
    "skills": ["python", "ai"]
  }
]
```

```bash
PYTHONPATH=. .venv/bin/python tools/upwork_scan.py --import-json /tmp/jobs.json
```

## Timer

```bash
systemctl status reclaw-upwork-scan.timer
systemctl start reclaw-upwork-scan.service   # run now
journalctl -u reclaw-upwork-scan.service -n 50
```

## Notify

If `ALERT_WEBHOOK` is set in `.env` (Discord webhook URL), new matches get a short ping.

## Legal / product notes

- Prefer official API over scrapers.
- Do not auto-apply (ToS + reputation risk).
- Digests are for **you** to apply when free.

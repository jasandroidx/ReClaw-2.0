# Reddit & Facebook access from Hetzner ReClaw

**Honest status (2026-07-17):** From this datacenter IP, `www.reddit.com` JSON/API returns **HTTP 403 Blocked**. Facebook is a login/Graph-API world — not scrapeable cleanly without Meta credentials.

## Reddit — how we fix it

### What already works (implemented)

| Method | Tool | Notes |
|--------|------|--------|
| **PullPush** search API | `tools/reddit_heat.py` | `api.pullpush.io` — submissions search from datacenter |
| **Subreddit RSS** | `tools/reddit_heat.py` | `https://www.reddit.com/r/Indiana/.rss` works |
| **Heat watch** | `tools/heat_watch.py` | Reddit + SBOA cache snapshot |

```bash
cd /root/ReClaw-2.0
PYTHONPATH=. .venv/bin/python tools/reddit_heat.py --term "water rate hike"
PYTHONPATH=. .venv/bin/python tools/heat_watch.py --county Clark
```

### Full live Reddit API (optional upgrade)

1. Log into Reddit (personal or bot account) → https://www.reddit.com/prefs/apps  
2. Create app type **script**  
3. Put in `/root/ReClaw-2.0/.env`:

```bash
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=linux:reclaw-heat:v1.0 (by /u/YOUR_USER)
REDDIT_USERNAME=...   # script apps
REDDIT_PASSWORD=...
```

4. **If still 403 from Hetzner:** Reddit is blocking datacenter ASN. Options:
   - **Tailscale exit node** on home/residential machine → route reddit API through it  
   - **Residential HTTP proxy** in `HTTPS_PROXY`  
   - Keep using PullPush/RSS (good enough for heat keywords)

5. Library: `praw` once credentials work.

### What not to do

- Headless browser login farming (ToS / ban risk)  
- Claim “I read Facebook/Reddit live” when only PullPush ran  

---

## Facebook — how we fix it

Facebook does **not** offer a free “search all local groups” API for bots.

| Approach | Feasibility | Use |
|----------|-------------|-----|
| **Meta Graph API** (Page or User token) | Medium — app review for some scopes | Read **your** Page posts / insights |
| **Manual heat inbox** | High | Operator pastes links into `data/inbox/heat/` markdown |
| **Public Page RSS / third-party** | Low / fragile | Unreliable |
| **Scrape groups logged-in** | Bad idea | ToS, blocks, legal risk |

### Recommended Facebook workflow

1. Create `data/inbox/heat/` notes: URL + county + 1-line rage summary  
2. Optional: Meta developer app → long-lived Page token for **official county Pages only**  
3. Never scrape closed groups

```bash
mkdir -p /root/ReClaw-2.0/data/inbox/heat
# drop files like: 2026-07-17-winslow-water-fb.md
```

---

## Firecrawl (county sites / minutes)

- Key may be present but **credits exhausted** → PaymentRequired  
- Top up at https://firecrawl.dev/pricing  
- Then `tools/firecrawl_discovery.py` for county `.in.gov` minutes/PDFs  

---

## Priority after social

1. SBOA ingest (done)  
2. Reddit heat (done via PullPush)  
3. DLGF levy (done)  
4. One-county claims/AP or Gateway engagement uploads  
5. SOS/OpenCorporates for COI  

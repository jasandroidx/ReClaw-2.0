# OPERATIONS.md — ReClaw 2.0 Operational Handbook

## Safe Normal Operating Model

ReClaw 2.0 is designed around a **local-first, deterministic, least-privilege operational model**.

Key principles:
1. **Zero-Dollar Base Operation**: Run local heuristic models and seed data by default (`USE_LIVE_FETCH=false`, `ENABLE_LLM_ANALYSIS=false`). Cloud APIs are disabled unless explicitly enabled by operator configuration.
2. **Session Isolation**: Every pipeline execution creates an isolated directory in `data/sessions/<session_id>/` containing an audit trail, logs, and approval records (`CONFIRMED FROM REPOSITORY`).
3. **Explicit Gate Enforcement**: High-risk capabilities (`shell_exec`, `compliance_audit`, `public_data_live_fetch`) require recorded approvals in the session directory before execution (`CONFIRMED FROM REPOSITORY`).
4. **Durable Memory via Obsidian**: Output packages are saved as immutable Markdown files and JSON sidecars to `outputs/obsidian/` or the configured vault path (`RECLAW_OBSIDIAN_VAULT_PATH`).

---

## Local-First Operating Principle

- **Default Execution Mode**: Rely on cached seeds (`data/seeds/`), local heuristics (`agents/analyst.py`), and disk-backed Chroma vector search (`rag/`).
- **Resource Discipline**: Production host hardware is CPU-bound (`LIVE ENVIRONMENT NOTE`: Hetzner ~30 GB RAM CPU host; secondary VM ~15.6 GiB RAM CPU host). CPU execution must be prioritized over heavy, unquantified LLM model loading.
- **Privacy & Hygiene**: Private data, `.env` parameters, raw logs, and credentials must never leave the local security boundary.

---

## How to Inspect Status Without Changing State

Use these read-only status commands (`CONFIRMED FROM REPOSITORY`):

### Container & Service Status
```bash
# Inspect container status
docker compose ps

# Check API health endpoint
curl -sf http://127.0.0.1:8000/health

# Check County Queue status
curl -sf http://127.0.0.1:8000/county-queue/status
```

### Process & Listener Inspection (Host)
```bash
# Check listening TCP ports without modifying state
ss -ltnp | grep -E '8000|8081|18789|8100'

# Inspect systemd unit active state (read-only)
systemctl is-active reclaw-platform-mcp.service
```

### Pipeline & Session Audit Trail Inspection
```bash
# List recent session runs
ls -la data/sessions/

# Read session security log (replace <session_id> with target ID)
cat data/sessions/<session_id>/logs/security.log
```

---

## Logging & Troubleshooting Locations

- **Container Logs**:
  - `docker compose logs -f reclaw-api`
  - `docker compose logs -f openclaw-gateway`
  - `docker compose logs -f reclaw-dashboard`
- **Session Logs** (`CONFIRMED FROM REPOSITORY`):
  - `data/sessions/<session_id>/logs/security.log`
  - `data/sessions/<session_id>/logs/run.log`
- **Job Status Persistence**:
  - `data/runs/<job_id>.status.json` (`CONFIRMED FROM REPOSITORY` via `core/job_registry.py`)
- **RAG Chroma Database**:
  - `data/rag_chroma/`

---

## Startup & Deployment Paths

### Local Python Execution (`CONFIRMED FROM REPOSITORY`)
```bash
# 1. Environment setup
cp .env.example .env
pip install -r requirements.txt

# 2. Execute CLI run
python -m reclaw.cli run --county Pike --area Winslow
```

### Production Container Execution (`CONFIRMED FROM REPOSITORY`)
```bash
# 1. Start Docker stack in background
docker compose up -d

# 2. Run post-deploy health check
./scripts/post-deploy-healthcheck.sh
```

---

## Rollback Principles

1. **Reversible Changes First**: Always apply the smallest possible change.
2. **Container Rollback**: Revert to the previous image tag or commit if a container deployment fails:
   ```bash
   git checkout <previous_commit>
   docker compose up -d --build
   ```
3. **Data Protection**: Pipeline state is file-backed (`data/sessions/`, `data/runs/`). Rolling back code does not destroy past session audit logs or written Obsidian markdown files.
4. **Configuration Reversion**: Restore `.env` from backup if configuration edits cause service degradation.

---

## "Do Not Do This Blindly" Safety Rules

- **Do NOT run `docker system prune -a`**: This removes cached Docker layers and can delete volume-stored persistent data if not carefully configured.
- **Do NOT restart services during an active pipeline run**: Check `curl -sf http://127.0.0.1:8000/county-queue/status` before restarting `reclaw-api`.
- **Do NOT blindly execute model pulls (`ollama pull <model>`)**: Large models loaded on CPU hosts can consume excessive system RAM, leading to Out-Of-Memory (OOM) process termination (`LIVE ENVIRONMENT NOTE`).
- **Do NOT overwrite `.env` or production config files**: Always compare diffs before copying or overwriting environment configurations.
- **Do NOT expose internal ports to `0.0.0.0` publicly**: API and gateway ports must remain bound to loopback or protected behind Tailscale authentication.

---

## Minimal Operator Checklist Before Production Changes

- [ ] Verify git working tree status (`git status`).
- [ ] Ensure any code change is accompanied by automated test verification (`PYTHONPATH=. python3 -m pytest scripts/ tests/rag/ -v`).
- [ ] Inspect container health before starting changes (`docker compose ps`).
- [ ] Confirm no hardcoded secrets or sensitive parameters are present in proposed commits.
- [ ] Prepare a clear rollback path (git commit hash to revert to if deployment fails).

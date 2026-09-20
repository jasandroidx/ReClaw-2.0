# CONFIGURATION.md — ReClaw 2.0 Configuration Reference

## Configuration-File Inventory

The repository utilizes the following configuration files:

- `.env.example`: Template environment file providing variable names and default values (`CONFIRMED FROM REPOSITORY`).
- `.env` (`git-ignored`): Local runtime environment variable definitions (`CONFIRMED FROM REPOSITORY`).
- `docker-compose.yml`: Container orchestration file defining environment overrides, port mappings, and volume mounts (`CONFIRMED FROM REPOSITORY`).
- `core/config.py`: Centralized Python configuration module utilizing Pydantic Settings (`Settings` class) to parse environment variables with default fallbacks (`CONFIRMED FROM REPOSITORY`).

---

## Config Precedence

`CONFIRMED FROM REPOSITORY` (`core/config.py`):
Pydantic Settings evaluates configuration settings in the following order of precedence (highest to lowest):

1. **Explicit process environment variables** (e.g. `export RECLAW_ENV=prod`).
2. **`.env` file overrides** (loaded automatically via Pydantic `SettingsConfigDict(env_file=".env")`).
3. **Pydantic field defaults** defined in `core/config.py`.

Note: In Docker Compose environments (`docker-compose.yml`), the `environment` and `env_file` keys inject environment variables directly into container environments, taking precedence over local `.env` files inside the container context.

---

## Environment Variable Inventory

All environment variables used by the application, listed by name only. Sensitive variables are marked explicitly.

### System & Paths
- `RECLAW_ENV`: Deployment environment (`dev` | `staging` | `prod`).
- `LOG_LEVEL`: Logging verbosity (`INFO`, `DEBUG`, etc.).
- `RECLAW_OBSIDIAN_VAULT_PATH`: Target directory path for Obsidian vault exports.
- `RECLAW_OBSIDIAN_SUBDIR`: Target subdirectory inside vault for package exports.
- `RECLAW_KNOWLEDGE_PATH`: Path to Ravenstack knowledge base.

### Data & Execution Flags
- `USE_LIVE_FETCH`: Boolean (`true`/`false`) toggling live HTTP fetching vs. local seed usage.
- `FETCH_TIMEOUT`: Timeout in seconds for HTTP requests.
- `MAX_PROPERTIES_PER_COUNTY`: Property sample limit per county run.
- `WRITE_DRY_RUN`: Boolean (`true`/`false`) toggling dry-run mode for file writes.
- `JOB_TIMEOUT_SECONDS`: Maximum job execution duration.

### Model & Analysis Flags
- `ENABLE_LLM_ANALYSIS`: Boolean (`true`/`false`) enabling LLM analysis calls.
- `LLM_MODEL`: Target model identifier for Ollama / vLLM.

### API Credentials & Secret Tokens (`SENSITIVE`)
- `OPENCLAW_GATEWAY_TOKEN`: `SENSITIVE` — Bearer authentication token for OpenClaw gateway triggers.
- `RECLAW_GATEWAY_TOKEN`: `SENSITIVE` — Bearer authentication token for ReClaw API endpoints.
- `CENSUS_API_KEY`: `SENSITIVE` — API key for US Census Bureau data queries.
- `FIRECRAWL_API_KEY`: `SENSITIVE` — API key for Firecrawl scraping service.
- `OBSIDIAN_API_KEY`: `SENSITIVE` — API key for local Obsidian REST API plugin.
- `XAI_API_KEY`: `SENSITIVE` — API key for xAI/Grok services.
- `GEMINI_API_KEY`: `SENSITIVE` — API key for Google Gemini services.
- `GOOGLE_API_KEY`: `SENSITIVE` — API key for Google APIs.

### RAG & Chroma Configuration
- `RAG_MODEL`: Sentence-transformer embedding model identifier (default: `all-MiniLM-L6-v2`).
- `RAG_CHUNK_SIZE`: Text chunk token/character size.
- `RAG_CHUNK_OVERLAP`: Text chunk overlap size.
- `RAG_PERSIST_DIR`: Local disk path for Chroma vector storage (`data/rag_chroma`).
- `RAG_VAULT_SYNC_INTERVAL`: Automatic vault sync interval in seconds.

---

## Provider & Model Endpoint Configuration Map

- **Ollama Inference Engine**: `http://127.0.0.1:8080` (`CONFIRMED FROM REPOSITORY` via `README.md`).
  - `LIVE ENVIRONMENT NOTE`: Serves local models on CPU.
- **OpenClaw Gateway**: `http://127.0.0.1:18789` (`CONFIRMED FROM REPOSITORY` via `docker-compose.yml`).
- **ReClaw API**: `http://127.0.0.1:8000` (`CONFIRMED FROM REPOSITORY` via `docker-compose.yml`).
- **MCP HTTP Bridge**: `http://127.0.0.1:8100` (`CONFIRMED FROM REPOSITORY` via `README.md`).

---

## Docker & Network Configuration Map

`CONFIRMED FROM REPOSITORY` (`docker-compose.yml`):
- `openclaw-gateway`:
  - Network port: `127.0.0.1:18789:18789` (Bound to loopback).
  - Host resolution: `host.docker.internal:host-gateway`.
- `reclaw-api`:
  - Network port: `8000:8000` (Exposed on host interface).
  - Host resolution: `host.docker.internal:host-gateway`.
  - Environment overrides: `RECLAW_ENV=prod`, `RECLAW_OBSIDIAN_VAULT_PATH=/vault`.
- `reclaw-dashboard`:
  - Network port: `8081:8080` (Host port 8081 mapped to container port 8080).

---

## Healthcheck Configuration Map

`CONFIRMED FROM REPOSITORY` (`docker-compose.yml`):
- `reclaw-api`:
  - Command: `curl -f http://localhost:8000/health`
  - Interval: `30s`, Timeout: `5s`, Retries: `3`, Start period: `10s`.
- `reclaw-dashboard`:
  - Command: `python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/')"`
  - Interval: `30s`, Timeout: `5s`, Retries: `3`.

---

## Safe Configuration-Review Checklist

When inspecting or updating configuration settings:

1. Confirm `.env` is listed in `.gitignore` and has not been tracked in Git.
2. Verify sensitive variable fields contain non-default, secure tokens in production environments.
3. Check that `WRITE_DRY_RUN=true` or `USE_LIVE_FETCH=false` is set when running dry tests.
4. Verify directory paths (`RECLAW_OBSIDIAN_VAULT_PATH`, `RAG_PERSIST_DIR`) exist and have appropriate write permissions for UID 1000.
5. Inspect `docker-compose.yml` environment block to ensure container overrides do not unintentionally mask required `.env` values.

---

## "Never Commit" Guidance

- **Never commit `.env` files** containing live API keys, tokens, or private path names.
- **Never hardcode bearer tokens or API credentials** inside Python files (e.g. `core/config.py` uses Pydantic defaults and `secrets.token_urlsafe` for dynamic generation if omitted).
- **Never log secret values** during application startup or error handling.

---

## Unknowns Requiring Live Server Evidence

1. **Active `.env` Values**: The exact live settings configured in `/root/ReClaw-2.0/.env` on the production server cannot be determined from repository source files.
2. **Tailscale Funnel Token & URL Path Secrets**: Public access paths managed via Tailscale Funnel are maintained outside the git repository.
3. **Live API Key Validity**: Whether external keys (`CENSUS_API_KEY`, `FIRECRAWL_API_KEY`) are active or rate-limited requires runtime API checks.

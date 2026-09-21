# SECURITY_MODEL.md — ReClaw 2.0 Security Architecture & Principles

## Trust Boundaries

ReClaw 2.0 establishes four distinct trust boundaries:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. External Internet / Unstrusted Public APIs               │
│    (Public government sites, Census, Firecrawl, xAI, Gemini) │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Authenticated Access Boundary                             │
│    (Tailscale Tailnet, Bearer Token Auth on API & Gateway)  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Container & Host Isolation Boundary                      │
│    (Docker containers, non-root UID 1000, host volume mounts)│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Local Execution & Durable Memory Boundary                │
│    (Local session dirs, Obsidian Vault, ChromaDB vector)   │
└─────────────────────────────────────────────────────────────┘
```

---

## Local vs. Cloud Data Classification

- **Local Data (Restricted to Host/Vault)**:
  - Raw session logs and audit trails (`data/sessions/`).
  - Active credentials, `.env` files, and Bearer tokens.
  - Final Markdown analysis packages written to Obsidian vault.
  - Local Chroma vector database indexes (`data/rag_chroma/`).
- **Public / Shareable Data**:
  - Indiana public record data pulled from Gateway or USASpending.
  - Public skill definitions (`SKILL.md`) and open schemas.

---

## Secret Categories & Redaction Rules

`CONFIRMED FROM REPOSITORY` (`core/config.py`, `.env.example`):
Secrets are categorized into three primary classes:

1. **Gateway Bearer Tokens**: `OPENCLAW_GATEWAY_TOKEN`, `RECLAW_GATEWAY_TOKEN`.
2. **External Data Provider Keys**: `CENSUS_API_KEY`, `FIRECRAWL_API_KEY`, `OBSIDIAN_API_KEY`.
3. **External Model Provider Keys**: `XAI_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`.

### Redaction Requirements
- **Never print secret values** in terminal outputs, application logs, or error stack traces.
- **Display only masked strings** (e.g. `REDACTED` or first-4/last-4 characters) when confirming credential presence.
- **Redact secrets automatically** before serializing log payloads or session artifacts to disk.

---

## Tool Permission Categories

`CONFIRMED FROM REPOSITORY` (`core/security.py`):
Capabilities are explicitly declared in `DECLARED_CAPABILITIES` with assigned `RiskLevel`:

- **Read-Only / Low-Risk (`RiskLevel.LOW`)**:
  - `public_data_seed`: Read local seed JSON files.
  - `heuristic_analysis`: Run deterministic analysis rules.
  - `script_generate`: Generate short scripts from packages.
  - `visual_event_emit`: Emit dashboard status events.
  - `skill_scan` / `skill_vet`: Audit skill code and manifests.
- **Local-Write / Medium-Risk (`RiskLevel.MEDIUM`)**:
  - `public_data_live_fetch`: Perform live HTTP requests to public site APIs (`requires_approval=True`).
  - `obsidian_write`: Write generated package files to Obsidian vault.
  - `skill_install`: Enable or install agent skills (`requires_approval=True`).
  - `cell_create`: Create new dashboard room cell state.
- **External-Write & Destructive / High-Risk (`RiskLevel.HIGH`)**:
  - `shell_exec`: Execute arbitrary host shell commands (`requires_approval=True`).
  - `compliance_audit`: Deep red-flag compliance analysis (`requires_approval=True`).
  - `arbitrage_scan`: Marketplace scanning (`requires_approval=True`).

---

## Cloud-Disabled-by-Default Requirement

To ensure zero-dollar operation, privacy, and budget control:

- **Cloud APIs are disabled by default** (`ENABLE_LLM_ANALYSIS=false`, `USE_LIVE_FETCH=false`).
- **All pipeline runs use local heuristics and disk-stored seed data** unless explicitly toggled by operator configuration.

---

## Conditions for Future Cloud Routing

If cloud inference or cloud APIs are enabled in the future, the following prerequisites must be met:

1. **Explicit Operator Opt-In**: The operator must explicitly set runtime configuration flags in `.env`.
2. **Prompt & Payload Sanitization**: Internal path names, host IPs, and local usernames must be stripped from outgoing prompts.
3. **Provider Privacy Review**: Selected providers must commit to non-retention and non-training policies for API payload data.

---

## Absolute Exclusion Rule for Free / Cloud Models

**Zero-Data-Leakage Policy**: Free or cloud LLM endpoints must **NEVER** receive any of the following data types under any circumstances:

- `.env` contents, API keys, or bearer tokens.
- Private SSH keys or Tailscale credentials.
- Discord bot tokens or channel authorization headers.
- Raw production error logs or host environment dumps.
- User personal notes or unredacted vault files.

---

## Git Hygiene Requirements

- `.env` and local secrets files must remain listed in `.gitignore`.
- Pre-commit verification must confirm no credentials or secret keys are staged.
- Commit histories must be scanned to ensure private tokens are never committed.

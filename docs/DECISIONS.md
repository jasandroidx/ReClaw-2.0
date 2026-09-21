# DECISIONS.md — Architectural Decision Records (ADR)

This document records key architectural decisions, their context, and status.

---

## ADR Index

1. [ADR-001: Local Ollama and Heuristics as Default Inference Strategy](#adr-001-local-ollama-and-heuristics-as-default-inference-strategy)
2. [ADR-002: CPU Benchmark Measurements Overrule Model-Size Assumptions](#adr-002-cpu-benchmark-measurements-overrule-model-size-assumptions)
3. [ADR-003: Secondary VM Restricted to Small-Model Fallback Role](#adr-003-secondary-vm-restricted-to-small-model-fallback-role)
4. [ADR-004: Cloud AI Routing Disabled by Default](#adr-004-cloud-ai-routing-disabled-by-default)
5. [ADR-005: Explicit Approval and Rollback Plan Required for Production Configuration Changes](#adr-005-explicit-approval-and-rollback-plan-required-for-production-configuration-changes)
6. [ADR-006: Mandatory Durable Repo Documentation Foundation](#adr-006-mandatory-durable-repo-documentation-foundation)

---

## ADR-001: Local Ollama and Heuristics as Default Inference Strategy

- **Status**: Active
- **Date**: 2026-09-06
- **Context**: The platform must operate reliably under a zero-dollar budget constraint without depending on paid cloud API services for core functions.
- **Decision**: Set local heuristic analysis (`ENABLE_LLM_ANALYSIS=false`) and local Ollama inference as the default strategy. Cloud API integration is disabled by default.
- **Consequences**:
  - Eliminates external API costs and external data exposure risks.
  - Requires local CPU hardware resources to handle execution workloads.

---

## ADR-002: CPU Benchmark Measurements Overrule Model-Size Assumptions

- **Status**: Active
- **Date**: 2026-09-06
- **Context**: On CPU-only hosts, larger parameter models (e.g. 8B–13B) often exhibit poor token throughput and high memory consumption compared to smaller, optimized models.
- **Decision**: Model selection for local CPU execution must be driven by empirical benchmark performance rather than parameter count alone.
- **Consequences**:
  - Small models (e.g., Qwen 4B-class) are preferred if benchmarks demonstrate superior tokens-per-second and acceptable accuracy.
  - Model changes require benchmark proof before default deployment.

---

## ADR-003: Secondary VM Restricted to Small-Model Fallback Role

- **Status**: Active
- **Date**: 2026-09-06
- **Context**: The secondary VM has ~15.6 GiB RAM and no GPU VRAM. It previously suffered an OOM process crash while hosting a large model.
- **Decision**: Designate the secondary VM strictly as an emergency small-model fallback host. Large models must never be deployed on this VM.
- **Consequences**:
  - Prevents host crashes and memory exhaustion on the secondary VM.
  - Limits the secondary VM to lightweight inference tasks.

---

## ADR-004: Cloud AI Routing Disabled by Default

- **Status**: Active
- **Date**: 2026-09-06
- **Context**: Cloud AI services pose potential credential leakage risks, cost overheads, and data privacy concerns if unmonitored.
- **Decision**: Disable cloud AI routing by default across all platform modules. Cloud routing requires explicit operator enablement, sanitization, and review.
- **Consequences**:
  - Protects sensitive session data, credentials, and local notes from external transmission.
  - Requires manual operator intervention if cloud capabilities are desired.

---

## ADR-005: Explicit Approval and Rollback Plan Required for Production Configuration Changes

- **Status**: Active
- **Date**: 2026-09-06
- **Context**: Production downtime or unverified configuration edits disrupt live operations and risk data loss.
- **Decision**: Any change affecting production Docker settings, environment variables, systemd units, or application routes requires explicit operator confirmation and a verified rollback path.
- **Consequences**:
  - Reduces operational risk during maintenance or deployment.
  - Mandates clear pre-deployment review steps.

---

## ADR-006: Mandatory Durable Repo Documentation Foundation

- **Status**: Active
- **Date**: 2026-09-06
- **Context**: Operators and AI coding agents repeatedly spent time rediscovering architecture, security boundaries, and operational facts across sessions.
- **Decision**: Establish a mandatory set of structured, durable Markdown documentation files in `docs/` (`ARCHITECTURE.md`, `CONFIGURATION.md`, `OPERATIONS.md`, `INCIDENTS.md`, `SECURITY_MODEL.md`, `AGENT_STATE.md`, `DECISIONS.md`, `KNOWN_ISSUES.md`).
- **Consequences**:
  - Provides a single, version-controlled source of truth for future agents and human operators.
  - Keeps operational context updated directly inside the repository.

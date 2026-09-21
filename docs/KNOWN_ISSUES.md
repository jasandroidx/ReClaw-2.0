# KNOWN_ISSUES.md — Known Technical Issues & Tracking

This document details known technical issues, ambiguities, missing evidence, and safe next actions.

---

## Issue Index

1. [ISSUE-001: Docker Container Networking Ambiguity (`127.0.0.1` vs `172.18.0.1`)](#issue-001-docker-container-networking-ambiguity-127001-vs-1721801)
2. [ISSUE-002: Suspected False Container Healthcheck Indication](#issue-002-suspected-false-container-healthcheck-indication)
3. [ISSUE-003: Secondary VM Keep-Alive RAM Allocation Risk](#issue-003-secondary-vm-keep-alive-ram-allocation-risk)
4. [ISSUE-004: Lack of Formal CPU Inference Benchmark Evidence](#issue-004-lack-of-formal-cpu-inference-benchmark-evidence)
5. [ISSUE-005: Need for Automated Test Coverage Around Routing and Capabilities](#issue-005-need-for-automated-test-coverage-around-routing-and-capabilities)

---

## ISSUE-001: Docker Container Networking Ambiguity (`127.0.0.1` vs `172.18.0.1`)

- **Status**: Open / Investigating
- **What Is Confirmed**:
  - `CONFIRMED FROM REPOSITORY`: Inside Docker containers (`reclaw-api`, `openclaw-gateway`), `127.0.0.1` refers strictly to the container's local loopback network interface.
  - Services running on the host machine (e.g., host MCP bridge on 8100) are mapped via `extra_hosts: host.docker.internal:host-gateway` in `docker-compose.yml`.
- **What Evidence Is Missing**:
  - Live container routing verification demonstrating whether all internal requests reliably resolve `host.docker.internal` across restart cycles.
- **Safe Next Action**:
  - Review all service client configurations to ensure host-bound calls explicitly use `host.docker.internal` or bridge IP instead of `127.0.0.1`.
- **Required Live-Server Command**:
  ```bash
  docker exec reclaw-api curl -I http://host.docker.internal:8100/health
  ```

---

## ISSUE-002: Suspected False Container Healthcheck Indication

- **Status**: Open / Investigating
- **What Is Confirmed**:
  - `CONFIRMED FROM REPOSITORY`: `docker-compose.yml` configures health checks for `reclaw-api` via `curl -f http://localhost:8000/health`.
  - `/health` in `api/main.py` returns HTTP 200 OK as a static check.
- **What Evidence Is Missing**:
  - Proof of whether `/health` accurately reflects background worker viability or disk accessibility under heavy load.
- **Safe Next Action**:
  - Extend `/health` in `api/main.py` to perform light dependency checks (e.g., verifying session directory writeability).
- **Required Live-Server Command**:
  ```bash
  docker inspect --format='{{json .State.Health}}' reclaw-api
  ```

---

## ISSUE-003: Secondary VM Keep-Alive RAM Allocation Risk

- **Status**: Open / Under Observation
- **What Is Confirmed**:
  - `LIVE ENVIRONMENT NOTE`: The secondary VM watchdog sets `OLLAMA_KEEP_ALIVE=-1`, pinning models in CPU RAM permanently.
  - The secondary VM has ~15.6 GiB RAM and suffered a prior OOM failure when running a large model.
- **What Evidence Is Missing**:
  - Real-time RAM consumption metrics for the VM under concurrent task execution.
- **Safe Next Action**:
  - Ensure only small models (e.g. Qwen 4B-class) are loaded on the secondary VM.
- **Required Live-Server Command**:
  ```bash
  ssh root@<vm-ip> "free -m && ps aux --sort=-%mem | head -n 10"
  ```

---

## ISSUE-004: Lack of Formal CPU Inference Benchmark Evidence

- **Status**: Open / Action Item
- **What Is Confirmed**:
  - `LIVE ENVIRONMENT NOTE`: Larger models were observed to perform worse on CPU hardware than smaller models.
  - No automated benchmark suite currently exists in the repository to measure tokens-per-second or memory efficiency across models.
- **What Evidence Is Missing**:
  - Quantitative benchmark metrics comparing model quantization levels and parameter sizes on CPU.
- **Safe Next Action**:
  - Build a local benchmark harness script (`scripts/benchmark_cpu_inference.py`) to record tokens/sec and memory usage.
- **Required Live-Server Command**:
  ```bash
  PYTHONPATH=. python3 scripts/benchmark_cpu_inference.py --models qwen2.5:3b,llama3.2:3b
  ```

---

## ISSUE-005: Need for Automated Test Coverage Around Routing and Capabilities

- **Status**: Open / Technical Debt
- **What Is Confirmed**:
  - `CONFIRMED FROM REPOSITORY`: Unit tests exist for RAG (`tests/rag/`), but full integration test coverage for API gate enforcement and fallback routing is limited.
- **What Evidence Is Missing**:
  - Test suites verifying security gate rejections and fallback handling under simulated network/API failures.
- **Safe Next Action**:
  - Implement pytest fixtures in `tests/` testing `SecurityManager` denial flows and trigger endpoint error handling.
- **Required Live-Server Command**:
  ```bash
  PYTHONPATH=. python3 -m pytest tests/ -v
  ```

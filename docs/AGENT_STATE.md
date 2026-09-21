# AGENT_STATE.md — Durable Operational Facts for Coding Agents

This file contains durable, high-confidence facts and rules intended for AI coding agents working in this repository.

---

## High-Confidence Operating Facts

1. **CPU-Only Hardware Reality**:
   - `LIVE ENVIRONMENT NOTE`: Production Hetzner host has ~30 GB RAM and no usable GPU VRAM.
   - `LIVE ENVIRONMENT NOTE`: Secondary VM host has ~15.6 GiB RAM, zero GPU VRAM, and suffered a prior OOM failure when loading large models.
   - All local model operations run on CPU. High-parameter models (e.g. 13B+) risk triggering kernel OOM terminations.
2. **Local-First / Zero-Dollar Operating Principle**:
   - Cloud providers are disabled by default (`ENABLE_LLM_ANALYSIS=false`, `USE_LIVE_FETCH=false`).
   - Default pipeline runs use local heuristic analysis and local JSON seed files.
3. **Container Loopback Isolation Rule**:
   - Inside Docker containers (`reclaw-api`, `openclaw-gateway`), `127.0.0.1` refers to that container's loopback interface.
   - Use `host.docker.internal` (configured in `docker-compose.yml`) to reach host services or host-bound bridge ports.
4. **Keep-Alive RAM Overhead**:
   - Setting `OLLAMA_KEEP_ALIVE=-1` retains models permanently in CPU memory.
   - Do not enable global permanent keep-alive without verifying adequate host RAM reserves (`free -m`).
5. **Durable Memory & Personalities**:
   - Agent identities and operating rules reside in `SOUL.md` and `agents/<agent>/SOUL.md`.
   - Never overwrite agent memory, personality prompts, or existing session logs during refactoring.

---

## Non-Negotiable Rules for Coding Agents

1. **No Unsanctioned Production Changes**:
   - Never modify server configurations, Docker compose definitions, systemd unit files, or credentials without explicit human approval.
2. **Benchmark Before Model Changes**:
   - Do not replace default model selections without empirical CPU throughput and memory benchmarks.
3. **Small, Reversible Step Discipline**:
   - Apply minimal, incremental code modifications. Test every change before proceeding.
4. **Verify Work Using Read-Only Tools**:
   - After file edits, confirm success using `git status`, `git diff`, or file reading tools before marking tasks complete.
5. **Maintain Documentation Accuracy**:
   - Label static repo facts as `CONFIRMED FROM REPOSITORY` and server environment observations as `LIVE ENVIRONMENT NOTE`.

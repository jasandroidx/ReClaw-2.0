# INCIDENTS.md — Historical Incident Record & Operational Learnings

This document logs historical operational incidents, known live-environment failure modes, and containment strategies to prevent recurring issues.

---

## Incident Record Format

Each incident entry uses the following schema:

```markdown
### [INC-YYYYMMDD-XX] Incident Title

- **Status**: Investigating | Contained | Resolved | Historical
- **Component**: Affected service or subsystem
- **What Is Known**: Confirmed facts and observed behavior
- **What Is Not Known**: Unconfirmed hypotheses or missing metrics
- **Evidence To Collect Next Time**: Commands, logs, or metrics needed for diagnosis
- **Safe Containment Steps**: Reversible steps to restore stability without data loss
- **Prevention Ideas**: Structural or procedural changes to prevent recurrence
```

---

## Recorded Incident History & Live-Environment Notes

### [INC-20260901-01] CPU-Only vs Mistaken GPU Inference Assumption

- **Status**: Historical / Documented Rule
- **Component**: Model Inference Subsystem / Ollama
- **What Is Known**:
  - `LIVE ENVIRONMENT NOTE`: Both the primary Hetzner VPS (~30 GB RAM) and secondary Grok Bot VM (~15.6 GiB RAM) are CPU-only hosts with no usable GPU VRAM.
  - Initial deployment assumptions assumed GPU acceleration would be available for LLM inference.
- **What Is Not Known**: Exact CPU performance bounds across all model parameter sizes under heavy concurrent loads.
- **Evidence To Collect Next Time**: Output of `ollama ps`, system RAM usage (`free -h`), CPU load averages (`uptime`).
- **Safe Containment Steps**: Keep `ENABLE_LLM_ANALYSIS=false` in `core/config.py` by default. Fall back to local heuristic analysis routines (`agents/analyst.py`).
- **Prevention Ideas**: Document CPU-only reality in `docs/AGENT_STATE.md` and enforce benchmark-driven model selection.

---

### [INC-20260902-02] VM Ollama Memory Exhaustion / Runner Failure

- **Status**: Contained / Documented
- **Component**: Secondary VM / Ollama Service
- **What Is Known**:
  - `LIVE ENVIRONMENT NOTE`: The secondary VM previously experienced an Out-Of-Memory (OOM) crash when a large LLM model was loaded into CPU RAM.
  - The VM has ~15.6 GiB RAM and cannot support large parameter models (e.g. 13B+ parameters) without risking host instability.
- **What Is Not Known**: Exact process peak memory footprint prior to kernel OOM kill.
- **Evidence To Collect Next Time**: Kernel dmesg logs (`dmesg -T | grep -i oom`), journalctl for Ollama service (`journalctl -u ollama -e`).
- **Safe Containment Steps**: Restrict secondary VM model deployment to small-model fallbacks (e.g., Qwen 4B-class models).
- **Prevention Ideas**: Set strict model size ceilings on secondary hosts and maintain adequate RAM swap/buffer space.

---

### [INC-20260902-03] Permanent Model Residency Caused by `OLLAMA_KEEP_ALIVE=-1`

- **Status**: Live Environment Note / Under Observation
- **Component**: Secondary VM Watchdog / Ollama Config
- **What Is Known**:
  - `LIVE ENVIRONMENT NOTE`: The VM watchdog service currently configures `OLLAMA_KEEP_ALIVE=-1`, which keeps loaded models resident in CPU memory indefinitely.
  - While this eliminates model cold-start latency, it holds ~4–8 GB of RAM permanently, reducing available memory for other tasks.
- **What Is Not Known**: Impact of persistent model memory allocation on concurrent background jobs during high load.
- **Evidence To Collect Next Time**: `free -m` and `ps aux --sort=-%mem` during pipeline execution.
- **Safe Containment Steps**: Restart Ollama service if host memory becomes dangerously constrained (`systemctl restart ollama`).
- **Prevention Ideas**: Evaluate replacing `-1` with a finite keep-alive duration (e.g. `5m` or `15m`) after benchmarking memory usage under load.

---

### [INC-20260903-04] Larger Model Benchmarking Worse Than Smaller Model on CPU

- **Status**: Resolved / Strategy Established
- **Component**: Model Selection / Inference Pipeline
- **What Is Known**:
  - `LIVE ENVIRONMENT NOTE`: In CPU-only inference tests, larger models (e.g. 8B–13B parameters) performed worse in tokens-per-second and memory consumption than optimized smaller models (e.g., Qwen 4B-class).
  - Model parameter size does not linearly correlate with pipeline utility on CPU hardware.
- **What Is Not Known**: Optimal quantization formats (e.g., Q4_K_M vs Q8_0) across all candidate small models.
- **Evidence To Collect Next Time**: Execution time benchmarks, token throughput rates, and red-flag detection accuracy metrics.
- **Safe Containment Steps**: Prefer lightweight models for local CPU inference runs.
- **Prevention Ideas**: Require empirical benchmark measurements before changing default model configurations.

---

### [INC-20260904-05] ReClaw Container Endpoint Ambiguity (`127.0.0.1` vs `172.18.0.1`)

- **Status**: Under Investigation
- **Component**: Docker Networking / Container Connectivity
- **What Is Known**:
  - `CONFIRMED FROM REPOSITORY`: Inside `reclaw-api` container, `127.0.0.1` refers to the container's own loopback interface, not the host machine or other containers.
  - Attempts to reach services listening on host `127.0.0.1` from inside containers fail unless routed via `host.docker.internal` or bridge IP (`172.18.0.1`).
- **What Is Not Known**: Whether existing container configurations consistently use `host.docker.internal` for cross-container service communication.
- **Evidence To Collect Next Time**: Container routing table (`ip route`), curl tests from inside container (`docker exec reclaw-api curl -I http://host.docker.internal:8100`).
- **Safe Containment Steps**: Update container configurations to use `host.docker.internal` instead of `127.0.0.1` for host-bound calls.
- **Prevention Ideas**: Explicitly document Docker loopback isolation rules in `docs/ARCHITECTURE.md` and `docs/AGENT_STATE.md`.

---

### [INC-20260905-06] Suspected False Healthcheck Indication

- **Status**: Under Investigation
- **Component**: Docker Compose Healthcheck / `reclaw-api`
- **What Is Known**:
  - `CONFIRMED FROM REPOSITORY`: `docker-compose.yml` executes `curl -f http://localhost:8000/health` inside `reclaw-api`.
  - `LIVE ENVIRONMENT NOTE`: Operators observed instances where container healthchecks reported `healthy` while backend background tasks or downstream connectors were unresponsive.
- **What Is Not Known**: Root cause of healthcheck disconnect (e.g. `/health` returning HTTP 200 without checking database or downstream worker responsiveness).
- **Evidence To Collect Next Time**: Detailed `/health` payload analysis, Uvicorn worker logs, and downstream service connectivity tests.
- **Safe Containment Steps**: Perform deep health checks manually via `curl -sf http://127.0.0.1:8000/county-queue/status` when verifying service state.
- **Prevention Ideas**: Enhance `/health` endpoint logic to perform shallow dependency probes (e.g., testing Chroma disk access or session directory accessibility).

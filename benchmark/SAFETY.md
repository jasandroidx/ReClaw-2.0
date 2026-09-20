# Ollama Benchmark Safety Guidelines

## CPU-Only System Risks & Safety Gate

Running large language models on CPU-only hardware carries significant risk of memory exhaustion (OOM), system instability, and high CPU load.

### Key Rules & Restrictions:

1. **Memory Safety Gate**:
   - The harness inspects available system memory (`/proc/meminfo` or system metrics) prior to every test.
   - If available RAM falls below `2048 MB` (or `min_free_ram_mb` in config), execution aborts immediately with status `ABORTED_FOR_SAFETY`.

2. **Single Model Execution**:
   - Never run benchmarks for multiple large models concurrently.
   - The harness strictly benchmarks one model at a time.

3. **Finite Keep-Alive (`keep_alive`)**:
   - Do NOT set `OLLAMA_KEEP_ALIVE=-1` or indefinite model residency on CPU hosts.
   - Config default uses `keep_alive: "5m"` to ensure model memory is released automatically after benchmark completion.

4. **Context Window Safety**:
   - Context windows >= 16,384 tokens are blocked by default.
   - Only supply `--allow-large-ctx` if system RAM capacity has been verified.

5. **Production Hosts**:
   - Do NOT run this benchmark harness on a production host during active user workloads without prior human review and approval.
   - Never expose Ollama endpoints to the public internet.

6. **Resource Exhaustion Signals**:
   - If Ollama logs report runner crashes, core dumps, or `CUDA/CPU memory allocation failed`, stop benchmarking immediately and increase memory safety limits.

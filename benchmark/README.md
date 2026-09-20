# Local-Only CPU-Safe Ollama Benchmark Harness

A reproducible, local-only benchmark framework to evaluate CPU-bound local Ollama models using real performance measurements.

## Non-Invasive Safeguards & Architecture

- **No Production Code Changes**: This benchmark harness is strictly isolated inside `benchmark/`. It does not touch production application code, Docker Compose, systemd, or agent routing.
- **Opt-In & Disabled by Default**: The harness runs in `--dry-run` mode by default and will refusing live network requests unless explicitly given `--run` **and** `ALLOW_OLLAMA_BENCHMARK=true`.
- **No Automatic Model Pulling**: Models are never downloaded automatically. You must specify an exact model tag that is already pulled in your local Ollama instance.
- **No Service Restarts**: Ollama is never started, stopped, or restarted by this suite.
- **Redaction Utility**: All output responses and raw logs are processed through a redaction utility to ensure accidental tokens or key patterns are masked before saving.

---

## Getting Started

### 1. Configuration Setup

Copy the example configuration file:

```bash
cp benchmark/config.example.yaml benchmark/config.yaml
```

Modify `benchmark/config.yaml` as needed. Default values:
- Endpoint: `http://127.0.0.1:11434`
- Context sizes: `[2048, 4096, 8192]`
- Minimum free RAM safety limit: `2048 MB`

---

## Running Benchmarks

### Dry-Run Mode (Default / Safe)

Test the benchmark suite execution and verify report generation without contacting Ollama:

```bash
python3 benchmark/run_suite.py --dry-run
# OR
./benchmark/run_suite.sh --dry-run
```

### Manual Live Benchmark Run (Human Approval Required)

To execute against a local, approved Ollama instance with a specific model:

```bash
ALLOW_OLLAMA_BENCHMARK=true python3 benchmark/run_suite.py --run --model "llama3.2:1b"
# OR
ALLOW_OLLAMA_BENCHMARK=true ./benchmark/run_suite.sh --run --model "llama3.2:1b"
```

---

## Benchmark Reports & Metrics

Output artifacts are written to `benchmark/results/` (or your configured `--out-dir`):

1. **`raw_results_<timestamp>.jsonl`**: Detailed JSON record of every test run.
2. **`summary_<timestamp>.csv`**: Tabular CSV report of context sizes, response durations, and status labels.
3. **`summary_<timestamp>.md`**: Formatted Markdown summary table with status badges and safety notes.

### Result Statuses:

- **`🟢 PASS`**: Response completed successfully and met evaluation constraints.
- **`🟡 DEGRADED`**: Output returned but failed strict schema parsing (e.g. JSON validation error).
- **`🔴 FAIL`**: Request timed out, returned HTTP error, or encountered network failure.
- **`⚠️ ABORTED_FOR_SAFETY`**: Test aborted prior to execution because free RAM or swap dropped below minimum thresholds.

---

## Understanding Cold vs. Warm Performance

- **Cold Run**: The initial request for a model requires loading model weights into RAM/CPU cache. Measured time includes model allocation overhead.
- **Warm Run**: Subsequent requests execute with model weights already resident in memory, providing an accurate measure of steady-state CPU token generation speed.

---

## CPU Memory & Context Scaling Risks

On CPU-only hardware, context sizes scale non-linearly in RAM usage and processing time:
- Context sizes 2K, 4K, and 8K are tested sequentially.
- **16K+ contexts are refused by default** to prevent severe CPU thrashing and Out-Of-Memory (OOM) kernel panics. To override, pass `--allow-large-ctx`.

All claims regarding model speed, latency, or memory consumption MUST be backed by actual output reports in `benchmark/results/`.

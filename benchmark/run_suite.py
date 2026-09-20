#!/usr/bin/env python3
"""
Ollama Local CPU-Safe Benchmark Harness runner.

Opt-in benchmark suite designed for testing local CPU-bound Ollama instances.
Does NOT execute live HTTP requests unless explicitly run with `--run` AND `ALLOW_OLLAMA_BENCHMARK=true`.
"""

import argparse
import datetime
import json
import os
import platform
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Try importing yaml, fallback to basic json/yaml parser
try:
    import yaml
except ImportError:
    yaml = None

try:
    from benchmark.report import generate_reports
except ImportError:
    generate_reports = None


DEFAULT_CONFIG = {
    "endpoint": "http://127.0.0.1:11434",
    "timeout_seconds": 120,
    "keep_alive": "5m",
    "num_predict": 512,
    "min_free_ram_mb": 2048,
    "min_free_swap_mb": 512,
    "context_sizes": [2048, 4096, 8192],
    "output_dir": "benchmark/results",
    "redact_patterns": [
        r"(?i)(bearer\s+)[a-zA-Z0-9_\-\.]{10,}",
        r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*([^\s]+)",
        r"(?i)(https?://)[^:\s]+:[^@\s]+@",
    ]
}

SAFE_MAX_CONTEXT = 8192


def redact_text(text: str, patterns=None) -> str:
    """Redact sensitive patterns (API keys, passwords, bearer tokens) from text."""
    if not isinstance(text, str):
        return text
    if patterns is None:
        patterns = DEFAULT_CONFIG["redact_patterns"]

    redacted = text
    for pattern in patterns:
        try:
            regex = re.compile(pattern)
            def _mask(match):
                g = match.groups()
                if len(g) >= 2:
                    return f"{g[0]}: [REDACTED]"
                return "[REDACTED]"
            redacted = regex.sub(_mask, redacted)
        except Exception:
            pass
    return redacted


def get_system_metrics():
    """Retrieve system host details, RAM, swap, and CPU load average without external dependencies."""
    metrics = {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "load_avg": [0.0, 0.0, 0.0],
        "total_ram_mb": 0,
        "free_ram_mb": 0,
        "total_swap_mb": 0,
        "free_swap_mb": 0,
    }

    if hasattr(os, "getloadavg"):
        try:
            metrics["load_avg"] = list(os.getloadavg())
        except Exception:
            pass

    meminfo_path = Path("/proc/meminfo")
    if meminfo_path.exists():
        try:
            mem_data = {}
            for line in meminfo_path.read_text().splitlines():
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    if val.isdigit():
                        mem_data[key] = int(val)  # in kB

            if "MemTotal" in mem_data:
                metrics["total_ram_mb"] = mem_data["MemTotal"] // 1024
            if "MemAvailable" in mem_data:
                metrics["free_ram_mb"] = mem_data["MemAvailable"] // 1024
            elif "MemFree" in mem_data:
                metrics["free_ram_mb"] = mem_data["MemFree"] // 1024

            if "SwapTotal" in mem_data:
                metrics["total_swap_mb"] = mem_data["SwapTotal"] // 1024
            if "SwapFree" in mem_data:
                metrics["free_swap_mb"] = mem_data["SwapFree"] // 1024
        except Exception:
            pass

    return metrics


def check_safety_gate(config, metrics=None):
    """
    Evaluates system memory/swap thresholds against config.
    Returns (safe: bool, reason: str).
    """
    if metrics is None:
        metrics = get_system_metrics()

    min_free_ram = config.get("min_free_ram_mb", 2048)
    min_free_swap = config.get("min_free_swap_mb", 512)

    free_ram = metrics.get("free_ram_mb", 0)
    free_swap = metrics.get("free_swap_mb", 0)

    if metrics.get("total_ram_mb", 0) == 0:
        return True, "RAM metrics unavailable, proceeding with caution"

    if free_ram < min_free_ram:
        return False, f"Available RAM ({free_ram} MB) is below minimum safety threshold ({min_free_ram} MB)"

    if free_swap < min_free_swap and metrics.get("total_swap_mb", 0) > 0:
        return False, f"Available Swap ({free_swap} MB) is below minimum safety threshold ({min_free_swap} MB)"

    return True, "System safety checks passed"


def query_ollama_version(endpoint, timeout=5):
    """Get Ollama version string from endpoint if available."""
    url = f"{endpoint.rstrip('/')}/api/version"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Ollama-Benchmark-Harness/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("version", "unknown")
    except Exception:
        pass
    return "unknown"


def call_ollama_generate(endpoint, model, prompt, num_ctx, num_predict, keep_alive, timeout):
    """Send request to Ollama /api/generate endpoint."""
    url = f"{endpoint.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": keep_alive,
        "options": {
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        }
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json", "User-Agent": "Ollama-Benchmark-Harness/1.0"},
        method="POST"
    )

    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            duration = time.time() - start_time
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                response_text = body.get("response", "")
                return {
                    "success": True,
                    "duration": duration,
                    "response": response_text,
                    "eval_count": body.get("eval_count", 0),
                    "eval_duration": body.get("eval_duration", 0),
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "duration": duration,
                    "response": "",
                    "error": f"HTTP status {resp.status}"
                }
    except urllib.error.URLError as e:
        duration = time.time() - start_time
        return {
            "success": False,
            "duration": duration,
            "response": "",
            "error": f"URLError: {e.reason}"
        }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "success": False,
            "duration": duration,
            "response": "",
            "error": f"Exception: {str(e)}"
        }


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="CPU-Safe Ollama Benchmark Harness (Disabled by default)"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Simulate run without making API calls (default)",
    )
    group.add_argument(
        "--run",
        action="store_true",
        help="Execute benchmark against local Ollama instance (requires ALLOW_OLLAMA_BENCHMARK=true)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="",
        help="Exact Ollama model tag to benchmark (e.g. 'llama3.2:1b')",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="benchmark/config.yaml",
        help="Path to YAML/JSON configuration file",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="",
        help="Override Ollama API endpoint URL (default: http://127.0.0.1:11434)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="",
        help="Override output directory for benchmark results",
    )
    parser.add_argument(
        "--allow-large-ctx",
        action="store_true",
        help="Override safety check and allow context sizes >= 16K (16384+)",
    )
    return parser.parse_args(args)


def load_config(config_path, cli_args=None):
    config = dict(DEFAULT_CONFIG)
    path = Path(config_path)

    if not path.exists():
        example_path = Path("benchmark/config.example.yaml")
        if example_path.exists():
            path = example_path

    if path.exists():
        content = path.read_text(encoding="utf-8")
        if yaml is not None:
            data = yaml.safe_load(content) or {}
        else:
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                data = {}
        config.update(data)

    if cli_args:
        if cli_args.endpoint:
            config["endpoint"] = cli_args.endpoint
        if cli_args.out_dir:
            config["output_dir"] = cli_args.out_dir

    return config


def validate_config_and_args(args, config):
    errors = []

    model_tag = args.model or config.get("default_model", "")
    if args.run and not model_tag:
        errors.append("An explicit model tag must be provided via --model or config 'default_model'")

    if args.run:
        env_flag = os.getenv("ALLOW_OLLAMA_BENCHMARK", "").lower()
        if env_flag not in ("true", "1", "yes"):
            errors.append("Live benchmark execution requires environment variable ALLOW_OLLAMA_BENCHMARK=true")

    ctx_sizes = config.get("context_sizes", [])
    for ctx in ctx_sizes:
        if ctx >= 16384 and not args.allow_large_ctx:
            errors.append(f"Context size {ctx} exceeds safe CPU limit ({SAFE_MAX_CONTEXT}). Pass --allow-large-ctx to override.")

    return errors


def load_test_cases(test_cases_dir="benchmark/test_cases"):
    """Load test case JSON/YAML files from test_cases directory."""
    cases = []
    tc_dir = Path(test_cases_dir)
    if not tc_dir.exists():
        return cases

    for file in sorted(tc_dir.glob("*.json")):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                cases.extend(data)
            elif isinstance(data, dict):
                cases.append(data)
        except Exception:
            pass

    for file in sorted(tc_dir.glob("*.yaml")):
        if yaml is not None:
            try:
                data = yaml.safe_load(file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    cases.extend(data)
                elif isinstance(data, dict):
                    cases.append(data)
            except Exception:
                pass

    return cases


def run_benchmark(args, config):
    model = args.model or config.get("default_model", "synthetic_model")
    endpoint = config.get("endpoint", "http://127.0.0.1:11434")
    out_dir = Path(config.get("output_dir", "benchmark/results"))
    out_dir.mkdir(parents=True, exist_ok=True)

    test_cases = load_test_cases()
    if not test_cases:
        # Fallback dummy test cases if directory is not populated yet
        test_cases = [
            {"id": "short_response", "name": "Short Response", "prompt": "Say hello in one word.", "expected_type": "text"},
            {"id": "instruction_following", "name": "Instruction Following", "prompt": "List 3 colors.", "expected_type": "text"},
        ]

    results = []
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ollama_version = query_ollama_version(endpoint) if args.run else "dry-run"

    print(f"=== Starting Benchmark Suite ({'LIVE' if args.run else 'DRY-RUN'}) ===")
    print(f"Model: {model}")
    print(f"Endpoint: {endpoint}")
    print(f"Output directory: {out_dir}")

    context_sizes = config.get("context_sizes", [2048, 4096, 8192])

    for ctx in context_sizes:
        for idx, tc in enumerate(test_cases):
            sys_metrics = get_system_metrics()
            safe, reason = check_safety_gate(config, sys_metrics)

            cold_warm = "cold" if idx == 0 else "warm"
            record = {
                "timestamp": timestamp_str,
                "model": model,
                "endpoint": endpoint,
                "context_size": ctx,
                "test_id": tc.get("id", f"tc_{idx}"),
                "test_name": tc.get("name", "Test Case"),
                "cold_warm": cold_warm,
                "status": "PASS",
                "duration_seconds": 0.0,
                "output_size_bytes": 0,
                "response": "",
                "parse_validity": True,
                "error": None,
                "safety_abort_reason": None,
                "system_metrics": sys_metrics,
                "ollama_version": ollama_version,
            }

            if not safe:
                record["status"] = "ABORTED_FOR_SAFETY"
                record["safety_abort_reason"] = reason
                results.append(record)
                print(f"[ABORTED] {tc.get('id')} (ctx: {ctx}) - {reason}")
                break

            if args.dry_run or not args.run:
                record["status"] = "PASS"
                record["response"] = "[DRY-RUN SIMULATED RESPONSE]"
                record["duration_seconds"] = 0.01
                record["output_size_bytes"] = len(record["response"])
                results.append(record)
                print(f"[DRY-RUN] {tc.get('id')} (ctx: {ctx}) -> PASS")
            else:
                prompt = tc.get("prompt", "Hello")
                res = call_ollama_generate(
                    endpoint=endpoint,
                    model=model,
                    prompt=prompt,
                    num_ctx=ctx,
                    num_predict=config.get("num_predict", 512),
                    keep_alive=config.get("keep_alive", "5m"),
                    timeout=config.get("timeout_seconds", 120),
                )
                record["duration_seconds"] = round(res["duration"], 3)
                record["error"] = res["error"]
                if res["success"]:
                    resp_text = res["response"]
                    record["response"] = redact_text(resp_text, config.get("redact_patterns"))
                    record["output_size_bytes"] = len(resp_text.encode("utf-8"))

                    if tc.get("expected_type") == "json":
                        try:
                            json.loads(resp_text)
                            record["parse_validity"] = True
                            record["status"] = "PASS"
                        except Exception:
                            record["parse_validity"] = False
                            record["status"] = "DEGRADED"
                    else:
                        record["status"] = "PASS"
                else:
                    record["status"] = "FAIL"

                results.append(record)
                print(f"[{record['status']}] {tc.get('id')} (ctx: {ctx}) - {record['duration_seconds']}s")

    # Write JSONL raw output
    jsonl_path = out_dir / f"raw_results_{int(time.time())}.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"Raw results written to: {jsonl_path}")

    # Call report generator if available
    try:
        from benchmark.report import generate_reports
        generate_reports(jsonl_path, out_dir)
    except Exception as e:
        print(f"Report generation note: {e}")

    return results


if __name__ == "__main__":
    cli_args = parse_args()
    cfg = load_config(cli_args.config, cli_args)
    errs = validate_config_and_args(cli_args, cfg)
    if errs:
        print("Configuration validation failed:", file=sys.stderr)
        for err in errs:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    run_benchmark(cli_args, cfg)

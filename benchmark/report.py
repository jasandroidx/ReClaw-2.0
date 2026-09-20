#!/usr/bin/env python3
"""
Report generator for Ollama CPU-Safe Benchmark Harness.

Reads raw JSONL benchmark records and produces:
1. CSV summary table
2. Markdown summary report
"""

import csv
import json
import sys
from pathlib import Path


def generate_reports(jsonl_file_path, output_dir=None):
    jsonl_path = Path(jsonl_file_path)
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Results file not found: {jsonl_file_path}")

    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not records:
        print("No records found to generate report.")
        return

    out_dir = Path(output_dir) if output_dir else jsonl_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    base_name = jsonl_path.stem.replace("raw_results_", "summary_")
    csv_path = out_dir / f"{base_name}.csv"
    md_path = out_dir / f"{base_name}.md"

    # Write CSV summary
    fieldnames = [
        "timestamp",
        "model",
        "endpoint",
        "context_size",
        "test_id",
        "test_name",
        "cold_warm",
        "status",
        "duration_seconds",
        "output_size_bytes",
        "parse_validity",
        "error",
        "safety_abort_reason",
        "ollama_version",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow(r)

    # Write Markdown summary
    first = records[0]
    md_lines = [
        "# Ollama Benchmark Run Summary Report",
        "",
        f"- **Timestamp**: `{first.get('timestamp', 'N/A')}`",
        f"- **Model**: `{first.get('model', 'N/A')}`",
        f"- **Endpoint**: `{first.get('endpoint', 'N/A')}`",
        f"- **Ollama Version**: `{first.get('ollama_version', 'unknown')}`",
        f"- **Total Test Runs**: `{len(records)}`",
        "",
        "## Summary Results",
        "",
        "| Test ID | Context | Cold/Warm | Duration (s) | Output (Bytes) | Parse Valid | Status | Safety / Error Notes |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for r in records:
        status_label = r.get("status", "UNKNOWN")
        if status_label == "PASS":
            status_str = "🟢 PASS"
        elif status_label == "DEGRADED":
            status_str = "🟡 DEGRADED"
        elif status_label == "FAIL":
            status_str = "🔴 FAIL"
        elif status_label == "ABORTED_FOR_SAFETY":
            status_str = "⚠️ ABORTED_FOR_SAFETY"
        else:
            status_str = status_label

        note = r.get("safety_abort_reason") or r.get("error") or ""
        # sanitize pipe characters in markdown table
        note = note.replace("|", "/")

        md_lines.append(
            f"| `{r.get('test_id')}` | {r.get('context_size')} | {r.get('cold_warm')} | {r.get('duration_seconds')}s | {r.get('output_size_bytes')} B | {r.get('parse_validity')} | {status_str} | {note} |"
        )

    md_lines.extend([
        "",
        "## Interpretation Notes",
        "",
        "- **Cold vs Warm**: Cold runs include model loading overhead into memory; warm runs reflect steady-state CPU inference speed.",
        "- **Context Scaling**: Performance degrades non-linearly on CPU systems as context increases (2K -> 4K -> 8K).",
        "- **Status Labels**:",
        "  - `PASS`: Response completed successfully and met constraints.",
        "  - `DEGRADED`: Output returned but failed schema or structural validation.",
        "  - `FAIL`: Request timed out, returned error status, or failed unexpectedly.",
        "  - `ABORTED_FOR_SAFETY`: Test aborted prior to execution because system memory/swap fell below safety limits.",
    ])

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"CSV Summary written to: {csv_path}")
    print(f"Markdown Summary written to: {md_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        generate_reports(sys.argv[1])
    else:
        print("Usage: python report.py <path_to_raw_results.jsonl>")

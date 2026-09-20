import json
import pytest
from pathlib import Path
from benchmark.report import generate_reports


def test_generate_reports_creates_csv_and_md(tmp_path):
    records = [
        {
            "timestamp": "2026-09-20T20:00:00Z",
            "model": "llama3.2:1b",
            "endpoint": "http://127.0.0.1:11434",
            "context_size": 2048,
            "test_id": "test_1",
            "test_name": "Test One",
            "cold_warm": "cold",
            "status": "PASS",
            "duration_seconds": 0.5,
            "output_size_bytes": 10,
            "parse_validity": True,
            "error": None,
            "safety_abort_reason": None,
            "ollama_version": "0.3.0",
        },
        {
            "timestamp": "2026-09-20T20:00:01Z",
            "model": "llama3.2:1b",
            "endpoint": "http://127.0.0.1:11434",
            "context_size": 4096,
            "test_id": "test_2",
            "test_name": "Test Two",
            "cold_warm": "warm",
            "status": "ABORTED_FOR_SAFETY",
            "duration_seconds": 0.0,
            "output_size_bytes": 0,
            "parse_validity": False,
            "error": None,
            "safety_abort_reason": "Low RAM",
            "ollama_version": "0.3.0",
        },
    ]

    jsonl_file = tmp_path / "raw_results_12345.jsonl"
    with open(jsonl_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    generate_reports(jsonl_file, tmp_path)

    csv_file = tmp_path / "summary_12345.csv"
    md_file = tmp_path / "summary_12345.md"

    assert csv_file.exists()
    assert md_file.exists()

    md_content = md_file.read_text()
    assert "llama3.2:1b" in md_content
    assert "🟢 PASS" in md_content
    assert "⚠️ ABORTED_FOR_SAFETY" in md_content
    assert "Low RAM" in md_content

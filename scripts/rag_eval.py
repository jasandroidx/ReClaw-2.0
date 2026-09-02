#!/usr/bin/env python3
"""Run the hand-labeled RAG eval set against POST /rag/search."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

EVAL = Path("/root/ReClaw-2.0/tests/rag/eval_set.json")
URL = "http://127.0.0.1:8000/rag/search"


def search(q: str, top_k: int = 5) -> list[str]:
    body = json.dumps({"query": q, "top_k": top_k, "vault_only": True}).encode()
    req = urllib.request.Request(
        URL, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    paths = []
    for hit in data.get("results") or []:
        cit = (hit.get("chunk") or {}).get("citation") or {}
        paths.append(str(cit.get("source_path") or ""))
    return paths


def main() -> int:
    cases = json.loads(EVAL.read_text())
    ok = 0
    print(f"# RAG eval  n={len(cases)}  top_k=5")
    for case in cases:
        paths = search(case["q"])
        needle = case["expect_path_contains"]
        hit = any(needle in p for p in paths)
        ok += int(hit)
        mark = "PASS" if hit else "FAIL"
        top = paths[0].rsplit("/", 1)[-1] if paths else "(none)"
        print(f"{mark}  {case['id']:20}  top={top}")
    print(f"score {ok}/{len(cases)}")
    return 0 if ok == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())

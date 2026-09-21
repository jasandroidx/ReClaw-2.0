#!/usr/bin/env python3
"""
Add Ollama model rows to openclaw.json with a SURGICAL text edit.

Two lessons from taking the gateway down with a full rewrite:

1. The config is JSON5 (comments and trailing commas are legal). A
   json.dumps() rewrite silently destroys those. So this never reparses or
   reserialises the whole file -- it locates the ollama provider's models
   array by bracket matching and splices only that span. Every other byte,
   including comments and formatting, is preserved exactly.

2. Emptying the array is what the schema rejected (gateway exited 78,
   EX_CONFIG). This only ADDS rows in the same {id, name} shape as the
   entries that boot fine today, so it stays inside the known-good schema.

Dry-run by default. Prints an exact before/after of the spliced span.
Use scripts/openclaw_safe_apply.sh to apply with validation and rollback.
"""
from __future__ import annotations
import argparse, json, os, re, shutil, sys
from datetime import datetime
from pathlib import Path

ADD = ["qwen3:4b", "qwen3-4b-64k", "qwen3-coder:30b"]


def find_block(text: str, key: str, start: int = 0):
    """Byte span of the {...} or [...] value for `key`, by bracket matching."""
    m = re.search(r'"%s"\s*:\s*([\[{])' % re.escape(key), text[start:])
    if not m:
        return None
    open_at = start + m.start(1)
    opener = m.group(1)
    closer = "]" if opener == "[" else "}"
    depth, i, in_str, esc = 0, open_at, False, False
    while i < len(text):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return open_at, i + 1
        i += 1
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--config", default=os.environ.get("OPENCLAW_CONFIG", str(Path.home() / ".openclaw" / "openclaw.json")))
    a = ap.parse_args()

    cfg = Path(a.config)
    if not cfg.is_file():
        print(f"FAIL: no config at {cfg}", file=sys.stderr)
        return 2
    text = cfg.read_text(encoding="utf-8")

    prov = find_block(text, "providers")
    if not prov:
        print('FAIL: no "providers" block found', file=sys.stderr)
        return 2
    oll = find_block(text, "ollama", prov[0])
    if not oll or oll[1] > prov[1]:
        print('FAIL: no "ollama" provider inside providers', file=sys.stderr)
        return 2
    models = find_block(text, "models", oll[0])
    if not models or models[1] > oll[1]:
        print('FAIL: ollama provider has no "models" array', file=sys.stderr)
        return 2

    span = text[models[0]:models[1]]
    try:
        rows = json.loads(span)
    except json.JSONDecodeError as e:
        print(f"FAIL: could not parse the models array ({e}).", file=sys.stderr)
        print("      It may use JSON5 syntax. Edit by hand in the Control UI.", file=sys.stderr)
        return 2
    if not isinstance(rows, list):
        print("FAIL: models is not an array", file=sys.stderr)
        return 2

    have = {r.get("id", r.get("name")) if isinstance(r, dict) else str(r) for r in rows}
    add = [t for t in ADD if t not in have]
    print(f"config : {cfg}")
    print(f"current: {sorted(x for x in have if x)}")
    if not add:
        print("nothing to add -- already present")
        return 0
    print(f"adding : {add}")

    # Match the shape already in the file: dict rows if it holds dicts.
    dict_style = any(isinstance(r, dict) for r in rows) or not rows
    new_rows = rows + ([{"id": t, "name": t} for t in add] if dict_style else add)

    line_start = text.rfind("\n", 0, models[0]) + 1
    lead = text[line_start:models[0]]
    base = len(lead) - len(lead.lstrip())
    new_span = json.dumps(new_rows, indent=2)
    new_span = "\n".join((" " * base + ln) if i else ln for i, ln in enumerate(new_span.split("\n")))

    print("\n--- replacing ONLY this span (everything else byte-identical) ---")
    print(f"old ({models[1]-models[0]} bytes):\n{span[:300]}")
    print(f"\nnew ({len(new_span)} bytes):\n{new_span[:400]}")

    if not a.apply:
        print("\nDry run. Nothing written. Re-run with --apply.")
        return 0

    out = text[:models[0]] + new_span + text[models[1]:]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = cfg.with_suffix(f".json.bak-{stamp}")
    shutil.copy2(cfg, bak)
    tmp = cfg.with_suffix(".json.tmp")
    tmp.write_text(out, encoding="utf-8")
    os.replace(tmp, cfg)
    print(f"\nbackup: {bak}")
    print(f"wrote : {cfg}")
    print(f"REVERT: cp {bak} {cfg} && docker restart openclaw-gateway")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

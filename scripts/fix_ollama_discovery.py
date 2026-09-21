#!/usr/bin/env python3
"""
Re-enable Ollama model auto-discovery in OpenClaw.

THE ACTUAL PROBLEM (per docs.openclaw.ai/providers/ollama/model-discovery):

  "A nonempty models.providers.ollama.models list selects manual models
   and skips discovery."

So the hand-written 3-model list is not incomplete -- it is what SUPPRESSES
discovery of the other pulled tags. Emptying it turns discovery back on and
every model you pull from then on shows up by itself.

  "an explicit self-hosted endpoint with models: [] remains eligible for
   discovery"

Also checks two things that silently break Ollama:
  - a /v1 suffix on baseUrl (selects OpenAI-compat mode; tool calling breaks)
  - a missing apiKey (loopback/private hosts use the "ollama-local" marker)

Cloud endpoints are never touched: emptying one would let it auto-register the
paid catalog from ollama.com.

Safety: dry-run by default, timestamped backup, result re-parsed before it
replaces the original, never restarts the gateway.

Usage:
  python3 scripts/fix_ollama_discovery.py                  # inspect + show plan
  python3 scripts/fix_ollama_discovery.py --apply          # empty the list
  python3 scripts/fix_ollama_discovery.py --manual --apply # opposite: pin by hand
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_CONFIG = Path(os.environ.get("OPENCLAW_CONFIG", str(Path.home() / ".openclaw" / "openclaw.json")))

# Only used with --manual. Discovery is the better path.
MANUAL_TAGS = ["qwen3:4b", "qwen3-4b-64k", "qwen3-coder:30b"]


def find_ollama_provider(node, path=""):
    """Yield (provider_dict, where) for each provider that speaks the ollama api."""
    if isinstance(node, dict):
        for k, v in node.items():
            here = f"{path}.{k}" if path else k
            if isinstance(v, dict) and (k == "ollama" or v.get("api") == "ollama"):
                yield v, here
            yield from find_ollama_provider(v, here)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from find_ollama_provider(v, f"{path}[{i}]")


def is_local(where: str, prov: dict) -> bool:
    """
    Only a LOCAL Ollama endpoint may be switched to discovery.

    Emptying a cloud provider's list would let it auto-register the paid
    catalog from ollama.com. Local-first means that never happens by accident.
    """
    if where.rsplit(".", 1)[-1].endswith("-cloud"):
        return False
    base = str(prov.get("baseUrl") or "").lower()
    if not base:
        return True  # implicit 127.0.0.1:11434
    if "ollama.com" in base:
        return False
    return any(
        marker in base
        for marker in ("127.0.0.1", "localhost", "host.docker.internal", "::1", ".local", "192.168.", "10.", "172.")
    )


def tag_of(entry):
    """Model rows are objects ({id, name, ...}); older configs used bare strings."""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return str(entry.get("id") or entry.get("name") or "?")
    return "?"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--manual", action="store_true", help="pin tags by hand instead of enabling discovery")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = ap.parse_args()

    cfg = Path(args.config)
    if not cfg.is_file():
        print(f"FAIL: config not found: {cfg}", file=sys.stderr)
        return 2
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"FAIL: {cfg} is not valid JSON ({e}). Not touching it.", file=sys.stderr)
        return 2

    providers = list(find_ollama_provider(data))
    if not providers:
        print("FAIL: no ollama provider found under models.providers.", file=sys.stderr)
        print("      Check the raw JSON: openclaw config schema, or the Raw JSON editor", file=sys.stderr)
        print("      in the Control UI at http://127.0.0.1:18789", file=sys.stderr)
        return 2

    changed = False
    for prov, where in providers:
        models = prov.get("models")
        tags = [tag_of(m) for m in models] if isinstance(models, list) else []
        print(f"\n{where}")
        print(f"  baseUrl : {prov.get('baseUrl', '(unset)')}")
        print(f"  api     : {prov.get('api', '(unset)')}")
        print(f"  apiKey  : {'set' if prov.get('apiKey') else '(unset)'}")
        print(f"  models  : {len(tags)} -> {', '.join(tags) if tags else '[] (discovery enabled)'}")

        base = str(prov.get("baseUrl") or "")
        if base.rstrip("/").endswith("/v1"):
            print("  WARNING: baseUrl ends in /v1 -- that selects OpenAI-compat mode and")
            print("           breaks tool calling. Ollama needs the native API. Drop /v1.")
        if not prov.get("apiKey"):
            print('  NOTE: apiKey unset. Loopback/private hosts expect the "ollama-local" marker.')

        if not is_local(where, prov):
            print("  skip  : not a local endpoint -- leaving it alone so no paid catalog")
            print("          gets auto-registered.")
            continue

        if args.manual:
            have = {tag_of(m) for m in (models or [])}
            additions = [t for t in MANUAL_TAGS if t not in have]
            if not additions:
                print("  manual: nothing to add")
                continue
            rows = [{"id": t, "name": t} for t in additions]
            prov["models"] = (models or []) + rows
            print(f"  manual: adding {', '.join(additions)} (this KEEPS discovery off)")
            changed = True
        else:
            if isinstance(models, list) and not models:
                print("  plan  : already [] -- discovery is on, nothing to do")
                continue
            prov["models"] = []
            print(f"  plan  : clear {len(tags)} hand-written rows -> [] so discovery takes over")
            changed = True

    if not changed:
        print("\nNo change needed.")
        return 0
    if not args.apply:
        print("\nDry run. Re-run with --apply to write.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = cfg.with_suffix(f".json.bak-{stamp}")
    shutil.copy2(cfg, backup)
    print(f"\nbackup: {backup}")

    out = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    json.loads(out)
    tmp = cfg.with_suffix(".json.tmp")
    tmp.write_text(out, encoding="utf-8")
    os.replace(tmp, cfg)
    print(f"wrote:  {cfg}")
    print("\nNOT restarted. Next steps, in order:")
    print("  1. docker restart openclaw-gateway")
    print("  2. openclaw models list          # all 7 tags should appear")
    print("  3. openclaw models status")
    print(f"\nRevert if anything looks wrong:  cp {backup} {cfg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Report-only vault lint. No writes to notes. No LLM.

Checks Ravenstack Markdown for broken [[wikilinks]], orphans (no in/out
links), and missing status: in YAML frontmatter when frontmatter exists.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

VAULT = Path("/root/obsidian_vault/Ravenstack")
LINK = re.compile(r"\[\[([^\]|#]+)")
SKIP_PARTS = {".obsidian", ".git", "__pycache__"}


def note_keys(path: Path, root: Path) -> set[str]:
    rel = path.relative_to(root).with_suffix("").as_posix().lower()
    return {path.stem.strip().lower(), rel}


def peek_status(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    block = text[4:end]
    for line in block.splitlines():
        if line.lower().startswith("status:"):
            return line.split(":", 1)[1].strip().lower()
    return ""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=VAULT)
    args = p.parse_args()
    root = args.root
    files = [
        f
        for f in root.rglob("*.md")
        if not any(part in SKIP_PARTS for part in f.parts)
    ]
    by_key: dict[str, Path] = {}
    outgoing: dict[Path, set[str]] = {}
    status_missing: list[Path] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        st = peek_status(text)
        if st is not None and st == "":
            status_missing.append(path)
        outs = {m.group(1).split("|", 1)[0].strip().lower() for m in LINK.finditer(text)}
        outgoing[path] = outs
        for k in note_keys(path, root):
            by_key[k] = path
        by_key[path.name.lower()] = path

    broken: list[tuple[Path, str]] = []
    has_edge: set[Path] = set()
    for path, outs in outgoing.items():
        if outs:
            has_edge.add(path)
        for target in outs:
            dest = by_key.get(target)
            if dest is None:
                broken.append((path, target))
            else:
                has_edge.add(dest)

    orphans = [f for f in files if f not in has_edge]
    print(f"# Vault lint  root={root}")
    print(f"notes={len(files)}  broken_links={len(broken)}  orphans={len(orphans)}  missing_status={len(status_missing)}")
    print("\n## Broken wikilinks")
    for src, tgt in broken[:50]:
        print(f"- {src.relative_to(root)} -> [[{tgt}]]")
    if len(broken) > 50:
        print(f"- … {len(broken) - 50} more")
    print("\n## Orphans (no inbound or outbound wikilinks)")
    for src in orphans[:50]:
        print(f"- {src.relative_to(root)}")
    if len(orphans) > 50:
        print(f"- … {len(orphans) - 50} more")
    print("\n## Frontmatter present but status: missing")
    for src in status_missing[:50]:
        print(f"- {src.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import os
from pathlib import Path
from typing import List

def get_sorted_files_by_mtime(path: str | Path, reverse: bool = True, is_dir: bool = False, limit: int | None = None) -> List[Path]:
    """
    Optimized directory listing using os.scandir() instead of pathlib.Path.iterdir()
    or glob(). It is faster because it caches stat results.
    """
    path = Path(path)
    if not path.exists():
        return []

    entries = []
    with os.scandir(path) as it:
        for entry in it:
            if is_dir and not entry.is_dir():
                continue
            entries.append(entry)

    # Sort entries by cached st_mtime
    entries.sort(key=lambda e: e.stat().st_mtime, reverse=reverse)

    if limit is not None:
        entries = entries[:limit]

    return [Path(e.path) for e in entries]

def get_sorted_glob_by_mtime(path: str | Path, pattern: str, reverse: bool = True, limit: int | None = None) -> List[Path]:
    """
    Optimized glob listing. Since os.scandir doesn't support recursive globbing natively,
    for simple 1-level globs like '*.json', we can filter manually.
    """
    path = Path(path)
    if not path.exists():
        return []

    # Check if it's a simple pattern (no directories/wildcards like **/)
    if '/' not in pattern and '**' not in pattern:
        import fnmatch
        entries = []
        with os.scandir(path) as it:
            for entry in it:
                if fnmatch.fnmatch(entry.name, pattern):
                    entries.append(entry)

        entries.sort(key=lambda e: e.stat().st_mtime, reverse=reverse)

        if limit is not None:
            entries = entries[:limit]

        return [Path(e.path) for e in entries]

    # Fallback to pathlib for complex patterns
    files = list(path.glob(pattern))
    files.sort(key=lambda p: p.stat().st_mtime, reverse=reverse)

    if limit is not None:
        files = files[:limit]

    return files

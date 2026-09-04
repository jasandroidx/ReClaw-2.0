"""
core/fs_utils.py — High-performance filesystem operations.
"""
import os
import fnmatch
from pathlib import Path
from typing import Iterator

def get_sorted_files_by_mtime(
    dir_path: Path | str,
    limit: int | None = None,
    directories_only: bool = False,
    pattern: str | None = None
) -> list[Path]:
    """
    Optimized file listing and sorting by modification time using os.scandir.
    Returns a list of pathlib.Path objects.
    """
    dir_path_obj = Path(dir_path)

    if not dir_path_obj.exists():
        return []

    entries = []
    with os.scandir(dir_path_obj) as it:
        for entry in it:
            if directories_only and not entry.is_dir():
                continue
            if pattern and not fnmatch.fnmatch(entry.name, pattern):
                continue
            entries.append(entry)

    entries.sort(key=lambda e: e.stat().st_mtime, reverse=True)

    if limit is not None:
        entries = entries[:limit]

    return [Path(e.path) for e in entries]

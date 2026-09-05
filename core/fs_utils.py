"""
core/fs_utils.py - File system utilities.
"""

import fnmatch
import os
from pathlib import Path
from typing import Optional

def get_sorted_files_by_mtime(
    dir_path: Path,
    pattern: str = "*",
    is_dir: Optional[bool] = None,
    reverse: bool = True
) -> list[Path]:
    """
    Optimized directory listing and sorting by modification time using os.scandir().

    Args:
        dir_path: The directory path to scan.
        pattern: The filename pattern to match (e.g., '*.json').
        is_dir: If True, only directories are returned. If False, only files.
        reverse: If True (default), newest files first.

    Returns:
        List of Path objects sorted by modification time.
    """
    if not dir_path.exists():
        return []

    items = []
    with os.scandir(dir_path) as it:
        for entry in it:
            if not fnmatch.fnmatch(entry.name, pattern):
                continue
            if is_dir is True and not entry.is_dir():
                continue
            if is_dir is False and not entry.is_file():
                continue
            items.append(entry)

    items.sort(key=lambda e: e.stat().st_mtime, reverse=reverse)
    return [Path(e.path) for e in items]

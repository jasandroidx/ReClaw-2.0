import os
import fnmatch
from pathlib import Path

def get_sorted_files_by_mtime(dir_path: Path, directories_only: bool = False) -> list[Path]:
    """
    Return all files (or directories) in dir_path sorted by modification time (newest first).
    Optimized using os.scandir to avoid multiple stat() calls.
    """
    if not dir_path.exists() or not dir_path.is_dir():
        return []

    entries = []
    with os.scandir(dir_path) as it:
        for entry in it:
            if directories_only and not entry.is_dir():
                continue
            entries.append((entry, entry.stat().st_mtime))

    # Sort by mtime descending
    entries.sort(key=lambda x: x[1], reverse=True)
    return [Path(entry.path) for entry, _ in entries]

def get_sorted_glob_by_mtime(dir_path: Path, pattern: str) -> list[Path]:
    """
    Return files in dir_path matching pattern sorted by modification time (newest first).
    Optimized using os.scandir to avoid multiple stat() calls.
    """
    if not dir_path.exists() or not dir_path.is_dir():
        return []

    entries = []
    with os.scandir(dir_path) as it:
        for entry in it:
            if fnmatch.fnmatch(entry.name, pattern):
                entries.append((entry, entry.stat().st_mtime))

    # Sort by mtime descending
    entries.sort(key=lambda x: x[1], reverse=True)
    return [Path(entry.path) for entry, _ in entries]

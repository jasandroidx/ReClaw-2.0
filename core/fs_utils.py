import os
import fnmatch
from pathlib import Path

def get_sorted_files_by_mtime(dir_path: Path, reverse: bool = True) -> list[Path]:
    """
    Returns a list of files/directories in `dir_path` sorted by modification time.
    Uses os.scandir for performance to avoid redundant stat calls.
    """
    if not dir_path.exists():
        return []

    entries = []
    with os.scandir(dir_path) as it:
        for entry in it:
            entries.append((entry, entry.stat().st_mtime))

    sorted_entries = sorted(entries, key=lambda x: x[1], reverse=reverse)
    return [Path(entry.path) for entry, _ in sorted_entries]

def get_sorted_glob_by_mtime(dir_path: Path, pattern: str, reverse: bool = True) -> list[Path]:
    """
    Returns a list of files in `dir_path` matching `pattern` sorted by modification time.
    Uses os.scandir for performance to avoid redundant stat calls.
    """
    if not dir_path.exists():
        return []

    entries = []
    with os.scandir(dir_path) as it:
        for entry in it:
            if fnmatch.fnmatch(entry.name, pattern):
                entries.append((entry, entry.stat().st_mtime))

    sorted_entries = sorted(entries, key=lambda x: x[1], reverse=reverse)
    return [Path(entry.path) for entry, _ in sorted_entries]

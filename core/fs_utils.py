import os
import fnmatch
from pathlib import Path
from typing import List, Union

def get_sorted_files_by_mtime(directory: Union[Path, str], reverse: bool = True) -> List[Path]:
    """
    Returns a list of Path objects in the directory sorted by modification time.
    Uses os.scandir() to optimize stat() calls.
    """
    path = Path(directory)
    if not path.exists():
        return []

    entries = []
    with os.scandir(path) as it:
        for entry in it:
            entries.append((entry.stat().st_mtime, entry.path))

    entries.sort(key=lambda x: x[0], reverse=reverse)
    return [Path(p) for _, p in entries]

def get_sorted_glob_by_mtime(directory: Union[Path, str], pattern: str, reverse: bool = True) -> List[Path]:
    """
    Returns a list of Path objects in the directory matching the glob pattern,
    sorted by modification time.
    Uses os.scandir() to optimize stat() calls.
    """
    path = Path(directory)
    if not path.exists():
        return []

    entries = []
    with os.scandir(path) as it:
        for entry in it:
            if fnmatch.fnmatch(entry.name, pattern):
                entries.append((entry.stat().st_mtime, entry.path))

    entries.sort(key=lambda x: x[0], reverse=reverse)
    return [Path(p) for _, p in entries]

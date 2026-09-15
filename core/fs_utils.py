import os
import fnmatch
from pathlib import Path
from typing import List

def get_sorted_files_by_mtime(dir_path: Path, reverse: bool = True) -> List[Path]:
    """Return a sorted list of Paths in dir_path by modification time."""
    if not dir_path.exists() or not dir_path.is_dir():
        return []
    with os.scandir(dir_path) as it:
        entries = list(it)
    entries.sort(key=lambda e: e.stat().st_mtime, reverse=reverse)
    return [Path(e.path) for e in entries]

def get_sorted_glob_by_mtime(dir_path: Path, pattern: str, reverse: bool = True) -> List[Path]:
    """Return a sorted list of Paths matching pattern in dir_path by modification time."""
    if not dir_path.exists() or not dir_path.is_dir():
        return []
    with os.scandir(dir_path) as it:
        entries = [e for e in it if fnmatch.fnmatch(e.name, pattern)]
    entries.sort(key=lambda e: e.stat().st_mtime, reverse=reverse)
    return [Path(e.path) for e in entries]

def fast_rglob(dir_path: str, ext: str) -> List[str]:
    """Recursively yield file paths matching the extension. Faster than pathlib.rglob."""
    out = []
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        return out
    with os.scandir(dir_path) as it:
        for entry in it:
            if entry.is_dir(follow_symlinks=False):
                out.extend(fast_rglob(entry.path, ext))
            elif entry.name.endswith(ext):
                out.append(entry.path)
    return out

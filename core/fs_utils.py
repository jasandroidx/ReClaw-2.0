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

def fast_rglob(dir_path: str | Path, pattern: str) -> List[str]:
    """
    Recursively find all files matching a pattern using os.scandir().
    Faster alternative to glob.glob() and Path.rglob().
    Returns paths as strings to replace glob.glob directly.
    """
    results = []
    def _scan(path: str):
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        _scan(entry.path)
                    elif fnmatch.fnmatch(entry.name, pattern):
                        results.append(entry.path)
        except OSError:
            pass
    _scan(str(dir_path))
    return results

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

def fast_rglob(dir_path: Path, pattern: str = "*") -> List[Path]:
    """Recursively yield Paths matching pattern in dir_path using os.scandir for performance.
    Symlinks are not followed to prevent infinite loops."""
    result = []
    if not dir_path.exists() or not dir_path.is_dir():
        return result

    def _scan(path: str):
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if fnmatch.fnmatch(entry.name, pattern):
                        result.append(Path(entry.path))
                    if entry.is_dir(follow_symlinks=False):
                        _scan(entry.path)
        except PermissionError:
            pass

    _scan(str(dir_path))
    return result

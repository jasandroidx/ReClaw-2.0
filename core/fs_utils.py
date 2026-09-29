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

def fast_rglob(dir_path: Path, pattern: str):
    """
    Fast recursive glob using os.scandir to avoid redundant stat() calls.
    Follows symlink safety guidelines.
    Yields os.DirEntry instead of Path to avoid subsequent stat calls for is_file()
    """
    if not dir_path.exists() or not dir_path.is_dir():
        return
    stack = [str(dir_path)]
    while stack:
        current_dir = stack.pop()
        try:
            with os.scandir(current_dir) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                        if fnmatch.fnmatch(entry.name, pattern):
                            yield entry
                    elif fnmatch.fnmatch(entry.name, pattern):
                        yield entry
        except PermissionError:
            continue

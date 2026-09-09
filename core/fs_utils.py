import os
from pathlib import Path

def get_sorted_files_by_mtime(directory: str | Path, reverse: bool = True) -> list[Path]:
    """
    Returns a list of Path objects for all files in the given directory,
    sorted by modification time. Uses os.scandir for performance.
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return []

    entries = []
    with os.scandir(dir_path) as it:
        for entry in it:
            if entry.is_file():
                entries.append(entry)

    # Sort entries by modification time
    entries.sort(key=lambda e: e.stat().st_mtime, reverse=reverse)

    return [Path(entry.path) for entry in entries]

def get_sorted_dirs_by_mtime(directory: str | Path, reverse: bool = True) -> list[Path]:
    """
    Returns a list of Path objects for all directories in the given directory,
    sorted by modification time. Uses os.scandir for performance.
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return []

    entries = []
    with os.scandir(dir_path) as it:
        for entry in it:
            if entry.is_dir():
                entries.append(entry)

    # Sort entries by modification time
    entries.sort(key=lambda e: e.stat().st_mtime, reverse=reverse)

    return [Path(entry.path) for entry in entries]

def get_sorted_glob_by_mtime(directory: str | Path, pattern: str, reverse: bool = True) -> list[Path]:
    """
    Returns a list of Path objects matching a pattern, sorted by mtime.
    Currently falls back to Path.glob as os.scandir does not support globbing natively,
    but this keeps the API consistent.
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return []

    paths = list(dir_path.glob(pattern))
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=reverse)
    return paths

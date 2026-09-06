"""
File system utilities for ReClaw.
"""
import os
import fnmatch
from pathlib import Path
from typing import List, Union

def get_sorted_files_by_mtime(
    dir_path: Union[Path, str],
    pattern: str = None,
    only_dirs: bool = False,
    only_files: bool = False,
    reverse: bool = True
) -> List[Path]:
    """
    Optimized directory listing and sorting by modification time using os.scandir().
    This avoids the overhead of pathlib.Path.glob() and multiple stat() calls.

    Args:
        dir_path: The directory to scan.
        pattern: Optional fnmatch pattern (e.g., "*.json").
        only_dirs: If True, only yield directories.
        only_files: If True, only yield files.
        reverse: If True (default), sort newest first.

    Returns:
        List of pathlib.Path objects sorted by mtime.
    """
    dir_obj = Path(dir_path)
    if not dir_obj.exists():
        return []

    entries = []
    try:
        with os.scandir(dir_obj) as it:
            for entry in it:
                if only_dirs and not entry.is_dir():
                    continue
                if only_files and not entry.is_file():
                    continue
                if pattern and not fnmatch.fnmatch(entry.name, pattern):
                    continue
                entries.append((entry.stat().st_mtime, entry.name))
    except FileNotFoundError:
        return []

    entries.sort(key=lambda x: x[0], reverse=reverse)
    return [dir_obj / name for _, name in entries]

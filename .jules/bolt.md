## 2026-09-06 - [Performance] Centralize os.scandir for fast mtime sorts
**Learning:** `pathlib.Path.glob` and `pathlib.Path.iterdir` combined with `key=lambda x: x.stat().st_mtime` causes redundant and slow stat system calls. Using `os.scandir` yields `os.DirEntry` objects which inherently cache `st_mtime` from the system call.
**Action:** Created `core/fs_utils.py` with `get_sorted_files_by_mtime` and `get_sorted_glob_by_mtime` helpers to utilize `os.scandir()` instead of `iterdir()`/`glob()`, and applied them across the codebase to prevent redundant OS stat calls.
## 2026-09-07 - [Performance] recursive directory traversal using os.scandir
**Learning:** `glob.glob` and `pathlib.Path.rglob` are significantly slower than recursive `os.scandir` when traversing large directory trees, especially for filtering specific file extensions like `.md`.
**Action:** Created `fast_rglob` in `core/fs_utils.py` and replaced `glob.glob` / `rglob` with `fast_rglob` in `core/mcp_connector.py` for `search` and `vault_stats`, reducing file system traversal overhead for Obsidian queries.

## 2026-09-06 - [Performance] Centralize os.scandir for fast mtime sorts
**Learning:** `pathlib.Path.glob` and `pathlib.Path.iterdir` combined with `key=lambda x: x.stat().st_mtime` causes redundant and slow stat system calls. Using `os.scandir` yields `os.DirEntry` objects which inherently cache `st_mtime` from the system call.
**Action:** Created `core/fs_utils.py` with `get_sorted_files_by_mtime` and `get_sorted_glob_by_mtime` helpers to utilize `os.scandir()` instead of `iterdir()`/`glob()`, and applied them across the codebase to prevent redundant OS stat calls.

## 2026-09-14 - [Performance] Use os.scandir to prevent redundant stat calls
**Learning:** Calling  individually on elements returned by  or  creates slow, redundant OS calls. Replaced with  to utilize 's inherently cached stats.
**Action:** Centralized fast file sorting by modifying  to import  and use  across MCP servers to avoid these redundant stat calls.

## 2026-09-14 - [Performance] Use os.scandir to prevent redundant stat calls
**Learning:** Calling `stat()` individually on elements returned by `pathlib.Path.iterdir()` or `pathlib.Path.glob()` creates slow, redundant OS calls. Replaced with `fs_utils.get_sorted_files_by_mtime` to utilize `os.scandir`'s inherently cached stats.
**Action:** Centralized fast file sorting by modifying `list_pipeline_sessions` to import `core.fs_utils` and use `get_sorted_files_by_mtime` across MCP servers to avoid these redundant stat calls.

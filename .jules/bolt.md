## 2026-09-06 - [Performance] Centralize os.scandir for fast mtime sorts
**Learning:** `pathlib.Path.glob` and `pathlib.Path.iterdir` combined with `key=lambda x: x.stat().st_mtime` causes redundant and slow stat system calls. Using `os.scandir` yields `os.DirEntry` objects which inherently cache `st_mtime` from the system call.
**Action:** Created `core/fs_utils.py` with `get_sorted_files_by_mtime` and `get_sorted_glob_by_mtime` helpers to utilize `os.scandir()` instead of `iterdir()`/`glob()`, and applied them across the codebase to prevent redundant OS stat calls.

## 2026-09-13 - [Performance] os.scandir fallback safety
**Learning:** While `os.scandir` is significantly faster than `pathlib.Path.glob` for shallow directory traversal by preventing redundant `stat()` system calls, it must be guarded by an `.exists()` check because it raises `FileNotFoundError` on non-existent directories, unlike `Path.glob` which safely yields an empty generator.
**Action:** When replacing `pathlib.Path.glob` with `os.scandir` in Python codebases, always explicitly check `dir.exists()` before entering the `with os.scandir(dir)` block to maintain parity with `glob`'s safe fallback behavior.
## 2025-02-12 - File Iteration Performance Optimization
**Learning:** Replaced remaining usages of `pathlib.Path.iterdir()` and `pathlib.Path.rglob()` with `os.scandir()` based alternatives (`get_sorted_files_by_mtime` and `fast_rglob`) across codebase. Specifically noted `pathlib.Path.iterdir()` and `.rglob()` are inefficient for large file systems because they incur redundant `os.stat` calls and lack caching compared to `os.scandir()`.
**Action:** Always prefer `os.scandir()` based utilities in `core/fs_utils.py` for directory iteration and recursive searching to minimize system calls and improve performance, especially on systems with large amounts of I/O operations.
## 2025-02-12 - Replaced pathlib.glob and iterdir for Performance
**Learning:** `pathlib.Path.rglob()`, `glob()`, and `iterdir()` create redundant `os.stat` system calls when modification times are needed, slowing down file traversals across large directories (e.g. the knowledge vault and rural data files). Replaced usages across `core/`, `scripts/`, `tools/`, and `benchmark/` with the performant `os.scandir` wrappers in `core/fs_utils.py`.
**Action:** For performance in ReClaw 2.0 when querying directory structures and their metadata, exclusively use `fast_rglob`, `get_sorted_files_by_mtime`, or `get_sorted_glob_by_mtime` from `core.fs_utils`.

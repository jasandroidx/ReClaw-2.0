## 2026-09-06 - [Performance] Centralize os.scandir for fast mtime sorts
**Learning:** `pathlib.Path.glob` and `pathlib.Path.iterdir` combined with `key=lambda x: x.stat().st_mtime` causes redundant and slow stat system calls. Using `os.scandir` yields `os.DirEntry` objects which inherently cache `st_mtime` from the system call.
**Action:** Created `core/fs_utils.py` with `get_sorted_files_by_mtime` and `get_sorted_glob_by_mtime` helpers to utilize `os.scandir()` instead of `iterdir()`/`glob()`, and applied them across the codebase to prevent redundant OS stat calls.

## 2026-09-13 - [Performance] os.scandir fallback safety
**Learning:** While `os.scandir` is significantly faster than `pathlib.Path.glob` for shallow directory traversal by preventing redundant `stat()` system calls, it must be guarded by an `.exists()` check because it raises `FileNotFoundError` on non-existent directories, unlike `Path.glob` which safely yields an empty generator.
**Action:** When replacing `pathlib.Path.glob` with `os.scandir` in Python codebases, always explicitly check `dir.exists()` before entering the `with os.scandir(dir)` block to maintain parity with `glob`'s safe fallback behavior.

## 2026-09-17 - [Performance] Generator slice dropping vs itertools
**Learning:** Wrapping a generator into a list comprehension just to slice it (e.g. `[ch for ch in text][:3]`) is inefficient because it builds an O(N) intermediate array before truncating. String slicing directly on the output of a generator (e.g., `"".join(x for x in data)[:3]`) results in `join` iterating all data *then* slicing the string, scaling at O(N) operations.
**Action:** Use `itertools.islice` (e.g. `itertools.islice((x for x in data), 3)`) before the `join` to limit iteration lazily, ensuring O(k) efficiency.

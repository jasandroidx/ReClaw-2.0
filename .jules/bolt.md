## 2026-09-10 - File System MTime Sorting Bottleneck

**Learning:** When sorting directories or listing files by modification time (`st_mtime`), using `pathlib.Path.glob()` or `pathlib.Path.iterdir()` followed by `lambda p: p.stat().st_mtime` creates a massive performance bottleneck. `Path.stat()` issues an additional stat system call for every file, leading to O(N) redundant I/O operations, especially noticeable when querying directories like `data/sessions` or `runs_dir` that grow unboundedly.

**Action:** Replace `Path.glob()` and `Path.iterdir()` with `os.scandir()`. `os.scandir()` caches the `stat` result (in `DirEntry.stat()`), effectively avoiding the redundant system calls. The centralized helpers `core.fs_utils.get_sorted_files_by_mtime` and `core.fs_utils.get_sorted_glob_by_mtime` should be used instead of raw `os.scandir` to ensure proper resource management and fallback.

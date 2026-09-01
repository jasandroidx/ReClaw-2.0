## 2025-02-05 - File Iteration Optimization
**Learning:** `glob.glob` with `recursive=True` and `Path.glob` are significantly slower than recursive `os.scandir` when we also need file stats (like `st_mtime`), because `os.scandir` yields `DirEntry` objects with cached stats.
**Action:** Always prefer `os.scandir` when iterating over many files if sorting by stat attributes like modified time, or searching recursively, as it avoids repeated `stat()` system calls.

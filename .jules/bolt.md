## 2026-07-20 - Optimize File System Iteration
**Learning:** pathlib.Path.glob() and iterdir() with .stat() can be slow for directories with many files because it does an extra stat system call. os.scandir() caches stat information (like st_mtime).
**Action:** Use os.scandir() instead of pathlib.Path.glob() and iterdir() when iterating over files to sort by st_mtime or check metadata.

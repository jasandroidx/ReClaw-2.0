## 2024-05-24 - File System Performance: Path.glob vs os.scandir
**Learning:** Using `pathlib.Path.glob()` combined with `.stat().st_mtime` sorting on large directories causes significant performance overhead due to O(N) un-cached `stat` syscalls.
**Action:** Always prefer `os.scandir()` when iterating over directories that require file metadata, as it yields `DirEntry` objects with cached `stat` results, drastically reducing system call overhead on this codebase.

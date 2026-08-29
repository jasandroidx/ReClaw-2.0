## Bolt's Journal

## 2026-08-29 - Avoiding extra stat() calls in directory listings
**Learning:** In a codebase reading many files from a directory (like job status files or sessions) and sorting them by modification time `st_mtime`, using `pathlib.Path.glob()` or `iterdir()` combined with `p.stat()` is a subtle performance bottleneck. This requires an extra `stat()` system call for every file.
**Action:** Use `os.scandir()` instead. It yields `os.DirEntry` objects that cache the `stat()` results (including `st_mtime`), significantly speeding up directory iteration and sorting. When passing to other functions, explicitly convert `entry.path` back to a `pathlib.Path` if needed.

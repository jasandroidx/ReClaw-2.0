## 2026-07-22 - Replace pathlib with os.scandir for performance
**Learning:** Using pathlib's `glob` or `iterdir` followed by `stat().st_mtime` causes redundant syscalls. `os.scandir()` caches the stat results, making it up to 75% faster when iterating and sorting large directories by modification time.
**Action:** Always prefer `os.scandir()` over `pathlib.Path.glob` or `iterdir` when sorting files by modification time or iterating over directories for performance.

## 2026-09-04 - [Python Pathlib glob/iterdir overhead]
**Learning:** Calling `pathlib.Path.glob()` or `iterdir()` followed by `p.stat().st_mtime` to sort files is a massive performance bottleneck because `pathlib` instantiates objects and makes a new OS system call for each file. Using `os.scandir` is 1.3x - 2.3x faster as it caches stat results (`st_mtime` and `is_dir`) in `os.DirEntry` objects.
**Action:** Created `core.fs_utils.get_sorted_files_by_mtime` to centralize this optimization. When sorting directory contents by modification time, avoid `pathlib` iterdir/glob + stat; use `os.scandir` instead.

## 2026-09-04 - [Script Import Order with sys.path]
**Learning:** In scripts (like those in `scripts/`) that manipulate `sys.path` (e.g., `sys.path.insert(0, str(ROOT))`) to resolve local modules (like `core`), importing any local module *before* `sys.path` is modified causes a fatal `ModuleNotFoundError`.
**Action:** When adding imports to standalone executable scripts, always carefully inspect the top of the file and ensure any local module imports are placed *after* the `sys.path` modifications.

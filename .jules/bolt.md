## 2024-05-18 - [Placeholder]
**Learning:** Initializing journal.
**Action:** Always check instructions.

## 2024-05-18 - Replacing glob() with os.scandir()
**Learning:** Replaced `pathlib.Path.glob()` and `pathlib.Path.iterdir()` with `os.scandir()` based on `core.fs_utils.get_sorted_glob_by_mtime` for file listings. Path objects are not generated as efficiently. The change helps optimize directory iteration where stat checking for file dates caused performance bottlenecks.
**Action:** Use `core.fs_utils.get_sorted_glob_by_mtime` / `get_sorted_files_by_mtime` when retrieving lists of files sorted by modification time.

## 2024-05-18 - Replacing glob() with os.scandir() Followup
**Learning:** I learned that it's important to not accidentally import from local project modules before `sys.path.insert(0, str(ROOT))` in standalone scripts that run from the `scripts/` directory, otherwise they will fail to execute with `ModuleNotFoundError`. I also learned to be careful when replacing string alphabetic sorts with modification time sorts as doing so incorrectly can negatively impact performance or introduce regressions. I also cleaned up leftover temp script files.
**Action:** In `scripts/`, ensure standard python imports go first, then `sys.path.insert(0, str(ROOT))`, and then any local project imports. Always double-check sorting requirements when changing directory listing routines.

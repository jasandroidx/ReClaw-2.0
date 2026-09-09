## 2026-09-09 - Initialization
**Learning:** `os.scandir()` optimizations require explicit implementations. The memory states that `get_sorted_files_by_mtime` exists in `core.fs_utils`, but neither the function nor the file exists in the current snapshot of the repository.
**Action:** When implementing `os.scandir()` optimizations, create the helper functions in `core/fs_utils.py` if they do not exist, and import them appropriately.

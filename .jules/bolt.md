## 2026-09-20 - Faster file system iterations
**Learning:** This codebase uses Python's `pathlib.Path.glob()` and `.rglob()` extensively for RAG and knowledge tasks, which can be a significant bottleneck due to hidden `stat` calls and object instantiation on Linux.
**Action:** Replaced usage with a centralized `fast_rglob` and `get_sorted_glob_by_mtime` from `core.fs_utils`, utilizing `os.scandir()`. This aligns with the codebase memory explicitly preferring `os.scandir()`.

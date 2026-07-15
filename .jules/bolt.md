## 2023-07-15 - File System Directory Listing Optimization
**Learning:** `pathlib.Path.glob` and `pathlib.Path.iterdir` combined with `.stat().st_mtime` sorting creates significant performance overhead when querying directories with thousands of files, which is a common scenario in ReClaw's job registry and session storage.
**Action:** Use `os.scandir` instead, which yields `os.DirEntry` objects. These objects cache `.stat()` attributes, significantly reducing system calls and providing a roughly ~2x speedup for directory listing and sorting operations in hot API endpoints.

## 2026-09-06 - Replacing rglob with fast_rglob for performance
**Learning:** `pathlib.Path.rglob()` is slow in Python, and this application has many operations that walk over directories (like Vault syncing, RAG index creation). `os.scandir` gives a direct performance boost without losing functionality.
**Action:** Replace `Path.rglob()` calls with a new helper `core.fs_utils.fast_rglob()` that leverages `os.scandir` recursively while maintaining the ability to filter via string matching or `fnmatch`.

## 2026-09-06 - Replacing rglob with fast_rglob for performance
**Learning:** `pathlib.Path.rglob()` is slow in Python, and this application has many operations that walk over directories (like Vault syncing, RAG index creation). `os.scandir` gives a direct performance boost without losing functionality.
**Action:** Replace `Path.rglob()` calls with a new helper `core.fs_utils.fast_rglob()` that leverages `os.scandir` recursively while maintaining the ability to filter via string matching or `fnmatch`.

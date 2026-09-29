## 2026-09-06 - Optimize directory listing performance
**Learning:** `pathlib.Path.iterdir()` combined with `.stat()` requires a separate syscall per file. `os.scandir()` caches stat information (like `st_mtime`), preventing N redundant syscalls during sorts.
**Action:** Always prefer `os.scandir()` (or `core.fs_utils.get_sorted_files_by_mtime`) over `iterdir()` + `stat()` for directory sorts to avoid unnecessary file I/O overhead.

## 2026-09-29 - FastMCP Thread Blocking Deadlock
**Learning:** `mcp.server.fastmcp` (FastMCP) handles requests synchronously if defined as `def`, blocking the main event loop. If a tool like `project_sitrep` makes an HTTP request to its own server's public endpoint (hairpin/funnel self-probe), it deadlocks because the server cannot process the incoming check while the original tool is still blocking the thread waiting for it.
**Action:** Always define slow, blocking, or self-probing tools as `async def` and wrap any internal blocking calls (like subprocesses or `requests`) in `await asyncio.to_thread(...)` to avoid starving the MCP event loop.

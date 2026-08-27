## 2024-05-18 - Missing Knowledge Files Block Testing
**Learning:** The `KnowledgeManager` explicitly checks for the existence of `RAVENSTACK-ORACLE.md` and `RAVENSTACK-ARCHITECTURE.md` in the `knowledge/` directory upon initialization. If these are missing, it raises a `RuntimeError` on startup, blocking even basic imports of `api.main` for testing purposes.
**Action:** When working in local dev or test environments on a fresh clone, ensure these placeholder markdown files exist before running backend components or tests that rely on the API module.
## 2024-05-18 - FastMCP Dependency Version Conflict
**Learning:** This codebase relies on the `FastMCP` class from the `mcp` library (`mcp.server.fastmcp`). In MCP 2.x, `FastMCP` was renamed to `MCPServer`, and other APIs changed. Attempting to run with `mcp>=2.0` results in `ModuleNotFoundError`.
**Action:** When installing dependencies or running MCP server scripts locally, explicitly pin `mcp<2` (e.g., `pip install "mcp<2"`) to ensure compatibility with the existing v1 code.

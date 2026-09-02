#!/usr/bin/env python3
"""ReClaw MCP Engine — safe Grok connector bridge.

Exposes the consolidated oracle_mcp layer (13 connectors, orchestration) as MCP tools.
Read-first: write actions blocked at this boundary.

Grok Build (~/.grok/config.toml):
  [mcp_servers.reclaw-mcp]
  command = "ssh"
  args = ["root@YOUR_HOST", "/root/ReClaw-2.0/.venv/bin/python", "/root/ReClaw-2.0/scripts/reclaw_mcp_server.py"]

HTTP (tailnet only):
  MCP_TRANSPORT=streamable-http FASTMCP_HOST=127.0.0.1 FASTMCP_PORT=8101 \\
    python scripts/reclaw_mcp_server.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load .env before oracle_mcp imports connectors (setdefault — never override existing env)
_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip())

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from core.mcp_connector import ConnectorRegistry
from core.oracle_mcp import WRITE_ACTIONS, mcp as oracle

_TSNET_HOST = os.environ.get("TAILSCALE_HOST", "openclaw.tail20a090.ts.net")

# Connectors safe for generic query (read-oriented)
ALLOWED_CONNECTORS = {
    "github",
    "llm",
    "hetzner",
    "tailscale",
    "docker",
    "notion",
    "obsidian",
    "ollama",
    "huggingface",
    "reclaw_meta",
}

BLOCKED_QUERY_ACTIONS = {
    ("github", "create_comment"),
    ("obsidian", "write"),
}

mcp_server = FastMCP(
    "reclaw-mcp",
    instructions=(
        "ReClaw 2.0 MCP engine. Safe read-first tools: status, health, connector queries, "
        "orchestration. Writes (GitHub comments, Obsidian write) are blocked here. "
        "LLM queries respect daily cost cap."
    ),
    host=os.environ.get("FASTMCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("FASTMCP_PORT", "8101")),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1:8101",
            "localhost:8101",
            f"{_TSNET_HOST}",
            f"{_TSNET_HOST}:443",
        ],
    ),
)


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def _safe_query(connector: str, params: dict) -> dict:
    connector = connector.lower().strip()
    if connector not in ALLOWED_CONNECTORS:
        raise ValueError(
            f"Connector '{connector}' not allowed via MCP bridge. "
            f"Allowed: {sorted(ALLOWED_CONNECTORS)}"
        )
    action = params.get("action", "query" if connector == "llm" else None)
    if action and (connector, action) in BLOCKED_QUERY_ACTIONS:
        raise PermissionError(f"Write action '{connector}.{action}' blocked on MCP bridge")
    if (connector, action or "") in WRITE_ACTIONS:
        raise PermissionError(f"Write action '{connector}.{action}' blocked on MCP bridge")
    return oracle.query_sync(connector, params)


@mcp_server.tool()
def mcp_status() -> str:
    """Quick MCP engine status: spend, connectors, overall health."""
    return _json(oracle.quick_status_sync())


@mcp_server.tool()
def mcp_health() -> str:
    """Phone-friendly health: docker, tailscale, connector count."""
    return _json(oracle.orchestrate_sync("quick_health"))


@mcp_server.tool()
def mcp_list_connectors() -> str:
    """List all registered MCP connectors."""
    return _json({"connectors": ConnectorRegistry.list()})


@mcp_server.tool()
def mcp_connector_health() -> str:
    """Per-connector health scores and overall status."""
    overall = oracle.query_sync("reclaw_meta", {"action": "overall_health"})
    unhealthy = oracle.query_sync("reclaw_meta", {"action": "unhealthy_connectors"})
    return _json({"overall": overall.get("result"), "unhealthy": unhealthy.get("result")})


@mcp_server.tool()
def mcp_heal_docker() -> str:
    """Check docker containers; report unhealthy (log/recommend only, no auto-restart)."""
    return _json(oracle.orchestrate_sync("auto_heal_docker"))


@mcp_server.tool()
def mcp_query(connector: str, action: str, params_json: str = "{}") -> str:
    """Run a read-safe query on a connector. params_json: optional JSON string of extra params.

    Examples:
      connector=github action=search params_json='{"q":"ReClaw-2.0"}'
      connector=obsidian action=search params_json='{"query":"ReClaw"}'
      connector=llm action=query params_json='{"prompt":"hello"}'
    """
    extra = json.loads(params_json) if params_json.strip() else {}
    query_params = {"action": action, **extra}
    return _json(_safe_query(connector, query_params))


@mcp_server.tool()
def mcp_meta(action: str) -> str:
    """Run a reclaw_meta introspection action (list_connectors, overall_health, vault_stats, etc.)."""
    return _json(oracle.query_sync("reclaw_meta", {"action": action}))


@mcp_server.tool()
def mcp_help() -> str:
    """How to connect this MCP server to Grok Build or remote clients."""
    return f"""ReClaw MCP Engine (reclaw-mcp) — safe bridge to core/oracle_mcp.py

TOOLS (read-first):
  mcp_status, mcp_health, mcp_list_connectors, mcp_connector_health
  mcp_heal_docker, mcp_query, mcp_meta

BLOCKED: github.create_comment, obsidian.write (use reclaw-platform for vault writes)

GROK BUILD — add to ~/.grok/config.toml:
  [mcp_servers.reclaw-mcp]
  command = "ssh"
  args = ["root@YOUR_HOST", "{ROOT}/.venv/bin/python", "{ROOT}/scripts/reclaw_mcp_server.py"]

STDIO on server:
  {ROOT}/.venv/bin/python {ROOT}/scripts/reclaw_mcp_server.py

HTTP (bind localhost; expose via Tailscale/nginx only):
  MCP_TRANSPORT=streamable-http FASTMCP_PORT=8101 python scripts/reclaw_mcp_server.py

Daily LLM spend cap: MAX_MCP_DAILY_BUDGET in .env (default $2.00)
"""


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport not in ("stdio", "sse", "streamable-http"):
        transport = "stdio"
    mcp_server.run(transport=transport)  # type: ignore[arg-type]
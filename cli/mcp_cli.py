#!/usr/bin/env python3
"""MCP CLI - useful commands for ReClaw"""
import sys
from core.oracle_mcp import mcp
def help_text():
    return """
MCP CLI Commands:
  status          - Quick overall system status
  health          - Run quick health check
  connectors      - List all registered connectors
  heal_docker     - Check and report unhealthy docker containers
  meta <action>   - Run any reclaw_meta action
  query <name>    - Run a raw query on a connector
"""
def main():
    if len(sys.argv) < 2:
        print(help_text())
        return
    cmd = sys.argv[1].lower()
    if cmd == "status":
        print(mcp.quick_status_sync())
    elif cmd == "health":
        print(mcp.orchestrate_sync("quick_health"))
    elif cmd == "connectors":
        print(mcp.query_sync("reclaw_meta", {"action": "list_connectors"}))
    elif cmd == "heal_docker":
        print(mcp.orchestrate_sync("auto_heal_docker"))
    elif cmd == "meta":
        if len(sys.argv) < 3:
            print("Usage: mcp meta <action>")
            return
        print(mcp.query_sync("reclaw_meta", {"action": sys.argv[2]}))
    elif cmd == "query":
        if len(sys.argv) < 4:
            print("Usage: mcp query <connector> <action>")
            return
        params = {"action": sys.argv[3]}
        for arg in sys.argv[4:]:
            if "=" in arg:
                k, v = arg.split("=", 1)
                params[k] = v
        print(mcp.query_sync(sys.argv[2], params))
    else:
        print(help_text())
if __name__ == "__main__":
    main()
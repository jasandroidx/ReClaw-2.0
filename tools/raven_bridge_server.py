#!/usr/bin/env python3
# DO NOT RUN. DO NOT BIND :8100.
# 2026-08-18: this SSE server stole reclaw-platform's port and broke the fortress.
# Unit raven-mcp-bridge is masked. See vault ops/incidents/2026-08-18-mcp-8100-port-thief.md
import asyncio
import json
import os
import shutil
from typing import Optional
import httpx
from fastmcp import FastMCP

mcp = FastMCP("RavenKeepBridge")

STACK_ROOT = "/root/ReClaw-2.0"
COMPOSE_FILE = os.path.join(STACK_ROOT, "docker-compose.yml")
OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/generate"

@mcp.tool()
async def get_fleet_status() -> str:
    """Returns container status for ReClaw 2.0 stack."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", "-f", COMPOSE_FILE, "ps", "--format", "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        if proc.returncode != 0:
            return f"Docker error: {stderr.decode().strip()}"
        raw = stdout.decode().strip()
        if not raw:
            return "No active containers in stack."
        lines = [json.loads(l) for l in raw.splitlines() if l.strip()]
        return "\n".join([f"- **{c.get('Name', c.get('Service'))}**: `{c.get('State')}` ({c.get('Status')})" for c in lines])
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def manage_service(service_name: str, action: str) -> str:
    """Control service: restart, stop, start."""
    action = action.lower().strip()
    if action not in {"restart", "stop", "start"}:
        return f"Invalid action: {action}"
    clean_svc = "".join(c for c in service_name if c.isalnum() or c in ("-", "_"))
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", "-f", COMPOSE_FILE, action, clean_svc,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=25.0)
        return f"Result: {stdout.decode() or stderr.decode() or 'Success'}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_service_logs(service_name: str, tail_lines: int = 50) -> str:
    """Fetch last N lines of logs."""
    tail = min(max(1, tail_lines), 150)
    clean_svc = "".join(c for c in service_name if c.isalnum() or c in ("-", "_"))
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", "-f", COMPOSE_FILE, "logs", "--no-follow", "--tail", str(tail), clean_svc,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        return stdout.decode().strip() or stderr.decode().strip() or "No logs."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def query_local_ollama(prompt: str, model: str = "gemma4") -> str:
    """Run local Ollama inference on 11434."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(OLLAMA_ENDPOINT, json={"model": model, "prompt": prompt, "stream": False})
            return res.json().get("response", "Empty response") if res.status_code == 200 else f"HTTP {res.status_code}: {res.text}"
    except Exception as e:
        return f"Ollama error: {str(e)}"

@mcp.tool()
async def get_host_telemetry() -> str:
    """Get CPU load and disk headroom."""
    total, used, free = shutil.disk_usage("/")
    with open("/proc/loadavg") as f:
        load = f.read().strip()
    return f"Load: {load} | Root Disk Free: {free/(1024**3):.2f}GB / {total/(1024**3):.2f}GB"

if __name__ == "__main__":
    mcp.run(transport="sse", host="127.0.0.1", port=8100)

"""ReClaw 2.0 - Rural Data Faceless Channel Agent Swarm.

Clean, production-grade rebuild of OpenClaw patterns for Hetzner + local dev.
Focus: Researcher -> Analyst/RedFlag -> Orchestrator -> Obsidian markdown packages.

Architecture (OpenClaw-aligned):
- Gateway (api/) as control plane
- Agents with per-agent SOUL.md identity + session isolation
- Structured JSON handoffs only
- SecurityManager + approval gates for anything above low risk
- Direct Obsidian channel output

Entry points:
- python -m reclaw.cli run --county Pike --area Winslow
- uvicorn api.main:app (or docker) for the Gateway
"""

__version__ = "2.0.0"

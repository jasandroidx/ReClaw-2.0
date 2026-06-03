"""Agent implementations: Researcher, Analyst, Orchestrator (and future).

Each agent directory contains:
- SOUL.md (identity loaded at runtime — OpenClaw pattern)
- <agent>.py (the implementation, session + security aware)
"""

from .researcher import ResearcherAgent
from .analyst import AnalystAgent
from .orchestrator import Orchestrator

__all__ = ["ResearcherAgent", "AnalystAgent", "Orchestrator"]

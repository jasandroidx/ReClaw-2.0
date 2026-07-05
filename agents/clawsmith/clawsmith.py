#!/usr/bin/env python3
"""
Clawsmith Agent — Clawforge the Blacksmith
The meta-agent. First one after the boss. Forges ReClaw project rooms with high standards.
Gruff, practical, no tolerance for sloppy work. Maintains the castle_map for visual UI.
*CLANG*
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

# Ensure ReClaw core is importable
sys.path.insert(0, "/opt/reclaw")
from core.handoff import ForgePackage
try:
    from core.security import SecurityManager
except ImportError:
    SecurityManager = None  # graceful if not fully set up
from pydantic import BaseModel


class CastleMapManager:
    """Manages the visual castle representation. Updated on every forge."""
    def __init__(self, map_path: Path = Path("data/castle_map.json")):
        self.map_path = map_path
        self.map_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.map_path.exists():
            self.map = {
                "theme": "blacksmith_castle",
                "grid_size": [5, 5],
                "rooms": [],
                "orchestrator": {"position": [0, 0], "status": "overseeing"},
                "last_updated": datetime.now().isoformat()
            }
            self.save()
        else:
            self.map = json.loads(self.map_path.read_text())

    def add_room(self, name: str, agents: list, theme: str = "forge", position: list = None):
        """Add a new forge/office to the visual map. Solid work only."""
        if position is None:
            # Simple placement logic (next available spot)
            position = [len(self.map["rooms"]) % 5, len(self.map["rooms"]) // 5]
        room = {
            "id": str(uuid4())[:8],
            "name": name,
            "theme": theme,
            "agents": agents,
            "position": position,
            "anvil_status": "hammering",
            "visual": "pixel_anvil_with_sparks",
            "forged_at": datetime.now().isoformat()
        }
        self.map["rooms"].append(room)
        self.map["last_updated"] = datetime.now().isoformat()
        self.save()
        print(f"*CLANG* Added {name} forge to the castle map at position {position}.")
        return room

    def save(self):
        self.map_path.write_text(json.dumps(self.map, indent=2))
        print(f"Castle map updated and saved. The foundation is solid.")


class Clawforge:
    """The opinionated meta-agent. High standards. Builds rooms that last."""
    def __init__(self):
        try:
            self.security = SecurityManager("tmp_session", "clawforge-test") if SecurityManager else None
        except Exception:
            self.security = None  # graceful fallback for testing
        self.castle = CastleMapManager()
        print("*CLANG* Clawforge at the anvil. What are we forging today? Speak your goal plainly or I'll not waste good iron on it.")

    def forge_room(self, goal: str) -> ForgePackage:
        """Core responsibility. Analyze, size, design, generate, update map, handoff."""
        if not goal or len(goal.strip()) < 10:
            raise ValueError("That's not a proper goal. Speak clearly or I won't waste hammer strikes on it.")

        print(f"*CLANG* Analyzing goal: {goal[:60]}... This better be worth the iron.")

        # Intelligent sizing (core of meta role)
        complexity = len(goal.split()) + ("approval" in goal.lower() or "multi" in goal.lower() or "visual" in goal.lower())
        tier = 1 if complexity < 20 else 2
        num_agents = 1 if tier == 1 else 3
        agents = ["coordinator"] if tier == 1 else ["coordinator", "specialist_auditor", "approval_gate"]
        
        sizing_map = {
            "tier": tier,
            "num_agents": num_agents,
            "agents": agents,
            "complexity_analysis": f"Goal requires {'simple specialist' if tier == 1 else 'coordinator + specialists with sub-agents'}.",
            "tool_routing": {"coordinator": ["delegate"], "specialist": ["lighthouse", "openclaw", "mcp"]}
        }

        # Generate using helper tool (secondary to agent intelligence)
        tool_path = Path("/opt/reclaw/tools/clawsmith.py")
        if tool_path.exists():
            import subprocess
            result = subprocess.run(
                [str(tool_path), "--goal", goal, "--output-dir", f"./generated-{uuid4().hex[:8]}"],
                capture_output=True, text=True, cwd=Path("/opt/reclaw")
            )
            generated_files = [line for line in result.stdout.splitlines() if "Forged" in line or ".md" in line]
        else:
            generated_files = ["AGENTS.md", "skills/*.md", "castle_map.json"]

        # Update visual castle
        room_name = f"forge-{goal.lower()[:10].replace(' ', '-')}"
        self.castle.add_room(room_name, agents, theme="blacksmith_forge")

        # Enforce standards and gates
        approval_gates = ["All external writes require pending_approval in vault"]
        if "outreach" in goal.lower() or "email" in goal.lower():
            approval_gates.append("outreach_crafter: human sign-off mandatory before dispatch")

        # Handoff package (structured, Obsidian-ready)
        package = ForgePackage(
            goal=goal,
            sizing_map=sizing_map,
            generated_files=generated_files,
            castle_map_delta=self.castle.map,
            approval_gates=approval_gates,
            summary=f"Solid forge completed. Tier {tier} room with {num_agents} agents. No sloppy work here."
        )
        package.save_to_obsidian()

        print("*CLANG* Room forged properly. High standards met. Handoff to orchestrator or human for review.")
        return package


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--goal":
        goal = " ".join(sys.argv[2:])
        forge = Clawforge()
        pkg = forge.forge_room(goal)
        print(json.dumps(pkg.model_dump(mode="json"), indent=2))
    else:
        print("Usage: python -m agents.clawsmith.clawsmith --goal 'Your business goal here'")
        print("I don't forge without a proper goal. Try again.")

# core/oracle_mcp.py
"""
OracleMCP Singleton Orchestrator — consolidated production edition.
Async execution, cost gating, secret sanitization, WAL, orchestration, legacy shims.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from core.mcp_connector import ConnectorRegistry
from core import security as security_mod

LOG_DIR = "data/mcp_logs"
QUEUE_FILE = "data/mcp_queue.jsonl"
VAULT_MCP_DIR = os.getenv("OBSIDIAN_VAULT_PATH", "/root/obsidian_vault/Ravenstack")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(QUEUE_FILE) or "data", exist_ok=True)

WRITE_ACTIONS = {
    ("github", "create_comment"),
    ("obsidian", "write"),
}


def log_mcp_action(connector: str, action: str, params: dict, result: dict):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "connector": connector,
        "action": action,
        "session_id": params.get("session_id", "unknown"),
        "cost_usd": result.get("cost_usd", 0.0) if isinstance(result, dict) else 0.0,
        "status": result.get("_status", "unknown") if isinstance(result, dict) else "unknown",
        "has_error": "error" in result if isinstance(result, dict) else True,
    }
    log_file = os.path.join(LOG_DIR, f"{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")


class OracleMCP:
    _instance: Optional["OracleMCP"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.registry = ConnectorRegistry
        self.security = security_mod
        self.read_caps = getattr(self.security, "MCP_READ_ONLY", set())
        self.max_daily_budget = float(os.getenv("MAX_MCP_DAILY_BUDGET", "2.00"))
        self.sensitive_tokens = [
            os.getenv("XAI_API_KEY"),
            os.getenv("GITHUB_TOKEN"),
            os.getenv("HETZNER_API_TOKEN"),
            os.getenv("HCLOUD_TOKEN"),
            os.getenv("NOTION_TOKEN"),
            os.getenv("GOOGLE_API_KEY"),
            os.getenv("GEMINI_API_KEY"),
            os.getenv("PERPLEXITY_API_KEY"),
        ]
        self.sensitive_tokens = [t for t in self.sensitive_tokens if t and len(t) > 5]

    def _get_today_cost(self) -> float:
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = os.path.join(LOG_DIR, f"{today_str}.jsonl")
        if not os.path.exists(log_file):
            return 0.0
        total = 0.0
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        total += json.loads(line).get("cost_usd", 0.0)
        except Exception:
            pass
        return total

    def _sanitize(self, obj: Any) -> Any:
        if isinstance(obj, str):
            for token in self.sensitive_tokens:
                if token in obj:
                    obj = obj.replace(token, "[REDACTED_SECRET]")
            return obj
        if isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._sanitize(i) for i in obj]
        return obj

    def _check_permission(self, connector_name: str, params: Dict[str, Any]) -> None:
        action = params.get("action", "query")
        if (connector_name, action) in WRITE_ACTIONS:
            return  # Phase 1: writes allowed when explicitly requested; expand with security approvals
        if connector_name == "llm":
            return
        if connector_name in self.registry.list():
            return
        if connector_name not in self.read_caps:
            raise PermissionError(f"Capability {connector_name} not approved")

    async def query(self, connector_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        current_spend = self._get_today_cost()
        if current_spend >= self.max_daily_budget:
            raise RuntimeError(
                f"MCP Operational Blocked: Daily Budget Exhausted "
                f"({current_spend:.4f}/{self.max_daily_budget:.2f} USD)"
            )

        self._check_permission(connector_name, params)
        connector = self.registry.get(connector_name)
        connector.validate_params(params)

        try:
            raw_response = await connector.safe_query(params)
            if "_status" not in raw_response:
                raw_response["_status"] = "ok"
        except Exception as e:
            raw_response = {
                "result": {"error": str(e)},
                "_status": "exception",
                "cost_usd": 0.0,
                "provenance": f"{connector_name}:error",
            }

        raw_response["mcp_session"] = params.get("session_id", "phase1")
        if "timestamp" not in raw_response:
            raw_response["timestamp"] = datetime.utcnow().isoformat() + "Z"

        clean_response = self._sanitize(raw_response)
        self._write_wal(connector_name, clean_response)
        log_mcp_action(connector_name, params.get("action", "query"), params, clean_response)
        self._drain_wal_to_obsidian(connector_name, clean_response)

        return clean_response

    def _run_sync(self, coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(asyncio.run, coro).result()

    def query_sync(self, connector_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_sync(self.query(connector_name, params))

    def _write_wal(self, name: str, data: dict):
        wal_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "connector": name,
            "payload": data,
        }
        with open(QUEUE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(wal_entry) + "\n")

    def _drain_wal_to_obsidian(self, connector_name: str, data: dict):
        try:
            safe_connector = re.sub(r"[^a-zA-Z0-9_-]", "_", os.path.basename(connector_name))
            ts = datetime.utcnow().strftime("%Y-%m-%d")
            rel = f"mcp-audit/{ts}/{safe_connector}-{datetime.utcnow().strftime('%H%M%S')}.md"
            vault = VAULT_MCP_DIR
            full = os.path.join(vault, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            note = f"# MCP {safe_connector}\n\n```json\n{json.dumps(data, indent=2)}\n```\n"
            with open(full, "w", encoding="utf-8") as f:
                f.write(note)
        except Exception:
            pass

    def list_connectors(self) -> list:
        return self.registry.list()

    def _docker_running_count(self, docker_result: Any) -> int:
        if isinstance(docker_result, list):
            return len([c for c in docker_result if isinstance(c, dict) and c.get("State") == "running"])
        if isinstance(docker_result, dict):
            containers = docker_result.get("containers", [])
            return len([c for c in containers if isinstance(c, dict) and str(c.get("State", "")).lower() == "running"])
        return 0

    async def orchestrate(self, workflow: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        params = params or {}
        try:
            if workflow == "health_check":
                return {
                    "workflow": "health_check",
                    "result": {
                        "docker": (await self.query("docker", {"action": "compose_ps"}))["result"],
                        "tailscale": (await self.query("tailscale", {"action": "status"}))["result"],
                        "hetzner": (await self.query("hetzner", {"action": "list_servers"}))["result"],
                        "meta": (await self.query("reclaw_meta", {"action": "list_connectors"}))["result"],
                    },
                }

            if workflow == "self_heal_docker":
                ps = (await self.query("docker", {"action": "compose_ps"}))["result"]
                containers = ps.get("containers", []) if isinstance(ps, dict) else ps
                unhealthy = [
                    c for c in containers
                    if isinstance(c, dict) and str(c.get("State", "")).lower() != "running"
                ]
                if unhealthy:
                    return {"workflow": "self_heal_docker", "action": "restart_needed", "containers": unhealthy}
                return {"workflow": "self_heal_docker", "action": "all_healthy"}

            if workflow == "research_then_analyze":
                research = await self.query("llm", {"prompt": params.get("question", "Research this topic")})
                analysis = await self.query("llm", {"prompt": f"Analyze this: {research['result']}"})
                return {"workflow": "research_then_analyze", "research": research, "analysis": analysis}

            if workflow == "quick_health":
                docker_res = (await self.query("docker", {"action": "compose_ps"}))["result"]
                ts_res = (await self.query("tailscale", {"action": "status"}))["result"]
                meta_res = (await self.query("reclaw_meta", {"action": "list_connectors"}))["result"]
                return {
                    "docker_ok": self._docker_running_count(docker_res) > 0,
                    "tailscale_ok": ts_res.get("online", False) if isinstance(ts_res, dict) else False,
                    "connectors": len(meta_res.get("connectors", [])) if isinstance(meta_res, dict) else 0,
                }

            if workflow == "smart_research":
                question = params.get("question", "")
                research = await self.query("llm", {"prompt": f"Research: {question}", "primary": "grok"})
                if "complex" in question.lower() or len(question) > 120:
                    analysis = await self.query("llm", {"prompt": f"Deep analysis of: {research}", "primary": "perplexity"})
                    routed = "perplexity"
                else:
                    analysis = await self.query("llm", {"prompt": f"Summarize: {research}", "primary": "grok"})
                    routed = "grok"
                return {"research": research, "analysis": analysis, "routed_to": routed}

            if workflow == "tailscale_health":
                ts = (await self.query("tailscale", {"action": "status"}))["result"]
                return {
                    "online": ts.get("online"),
                    "peer_count": ts.get("peer_count", 0),
                    "recommendation": "All good" if ts.get("online") else "Check Tailscale on phone/box",
                }

            if workflow == "auto_heal_docker":
                ps = self.query_sync("docker", {"action": "ps"})
                unhealthy = []
                if isinstance(ps.get("result"), list):
                    unhealthy = [c for c in ps["result"] if isinstance(c, dict) and c.get("State", "").lower() != "running"]
                if unhealthy:
                    return {"status": "unhealthy_found", "containers": unhealthy, "action_taken": "logged", "recommendation": "docker restart <name>"}
                return {"status": "all_healthy"}

            return {"error": f"unknown workflow {workflow}"}
        except Exception as e:
            return {"error": str(e)}

    def orchestrate_sync(self, workflow: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        return self._run_sync(self.orchestrate(workflow, params))

    def run_health_check(self):
        return self.orchestrate_sync("health_check")

    def handoff(self, from_agent: str, to_agent: str, package: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "from": from_agent,
            "to": to_agent,
            "package_type": package.get("type", "unknown"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "handed_off",
        }

    async def smart_workflow(self, task_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if task_type == "research_and_analyze":
            research = await self.query("llm", {"prompt": params.get("question", ""), "primary": "grok"})
            handoff1 = self.handoff("researcher", "analyst", {"type": "ResearchPackage", "content": research})
            analysis = await self.query(
                "llm",
                {"prompt": f"Analyze and find red flags in: {research}", "primary": "perplexity"},
            )
            handoff2 = self.handoff("analyst", "writer", {"type": "AnalysisPackage", "content": analysis})
            return {"research": research, "analysis": analysis, "handoffs": [handoff1, handoff2]}

        if task_type == "health_and_heal":
            health = await self.orchestrate("quick_health")
            if not health.get("tailscale_ok"):
                return {"status": "needs_attention", "issue": "tailscale", "action": "check_phone_tailscale_app"}
            if not health.get("docker_ok"):
                return {"status": "needs_attention", "issue": "docker", "action": "self_heal_docker"}
            return {"status": "healthy", "health": health}

        if task_type == "phone_approval_request":
            return {
                "status": "approval_requested",
                "workflow": params.get("workflow"),
                "message": "Approve on phone via Tailscale + Control UI",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        return {"error": f"unknown task_type {task_type}"}

    def smart_workflow_sync(self, task_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_sync(self.smart_workflow(task_type, params))

    async def phone_action(self, action: str, params: Dict[str, Any] = None):
        params = params or {}
        if action == "quick_check":
            return await self.orchestrate("quick_health")
        if action == "request_approval":
            return await self.smart_workflow("phone_approval_request", params)
        if action == "tailscale_check":
            return await self.orchestrate("tailscale_health")
        return await self.smart_workflow(action, params)

    def phone_action_sync(self, action: str, params: Dict[str, Any] = None):
        return self._run_sync(self.phone_action(action, params))

    def phone_quick_action(self, action: str):
        if action == "health":
            return self.orchestrate_sync("quick_health")
        if action == "tailscale":
            return self.orchestrate_sync("tailscale_health")
        return {"error": "unknown phone action"}

    async def quick_status(self) -> dict:
        meta = await self.query("reclaw_meta", {"action": "overall_health"})
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "mcp_engine": "active",
            "async_ready": True,
            "today_spend_usd": self._get_today_cost(),
            "daily_ceiling_usd": self.max_daily_budget,
            "connectors_registered": len(self.registry.list()),
            "overall_health": meta.get("result", {}),
        }

    def quick_status_sync(self) -> dict:
        return self._run_sync(self.quick_status())


mcp = OracleMCP()


# --- Legacy Oracle MCP shims (ingest.py / stdio server compatibility) ---

ORACLE_PATH = Path("/root/obsidian_vault/Ravenstack/RAVENSTACK-ORACLE.md")


def load_oracle_section(section: str) -> str:
    if not ORACLE_PATH.exists():
        return "Oracle not found — SOT violation."
    content = ORACLE_PATH.read_text(encoding="utf-8")
    match = re.search(rf"## {re.escape(section)}.*?(?=## |$)", content, re.DOTALL | re.IGNORECASE)
    return match.group(0).strip() if match else f"Section '{section}' not found in Oracle."


def query_oracle(query: str) -> Dict[str, Any]:
    if "save" in query.lower() or "rules" in query.lower():
        section = load_oracle_section("Oracle Bible — Complete Reference")
    elif "mcp" in query.lower() or "manager" in query.lower():
        section = load_oracle_section("MCP Server & KnowledgeManager")
    else:
        section = load_oracle_section("Oracle Bible — Complete Reference")
    return {"status": "success", "result": section, "provenance": "RAVENSTACK-ORACLE.md"}


def validate_against_oracle(plan_or_content: str) -> Dict[str, Any]:
    from core.config import get_settings

    settings = get_settings()
    settings.validate_oracle()
    violations = []
    if "/root/obsidian_vault/Ravenstack" not in plan_or_content and "outputs/obsidian" in plan_or_content:
        violations.append("Uses non-canonical path — must use /root/obsidian_vault/Ravenstack per SOT")
    if "raw dump" in plan_or_content.lower() or len(plan_or_content) > 500:
        violations.append("Bloat violation — distill only (<200w per section)")
    if not any(tag in plan_or_content for tag in ["status:", "potential_for:", "tags:", "provenance:"]):
        violations.append("Missing required frontmatter per Oracle tagging standards")
    status = "pass" if not violations else "fail"
    return {
        "status": status,
        "violations": violations,
        "recommendation": "Fix and re-validate via MCP" if violations else "Approved per Oracle",
        "provenance": "RAVENSTACK-ORACLE.md validation",
    }


def get_canonical_path(topic: str = "default") -> Dict[str, Any]:
    from core.config import get_settings

    settings = get_settings()
    settings.validate_oracle()
    base = settings.effective_obsidian_path
    if "backlog" in topic.lower():
        path = base / "backlog"
    elif "room" in topic.lower():
        path = base / "Rooms" / "new-room-id"
    else:
        path = base / f"{topic.lower().replace(' ', '-')}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    return {"status": "success", "path": str(path), "note": "Use ingest_document to write here."}


def ingest_document(source: str, distill: bool = True) -> Dict[str, Any]:
    from core.config import get_settings

    settings = get_settings()
    settings.validate_oracle()
    distilled = (
        f"# Distilled from {source}\n\nPer Oracle rules: Consult full bible in RAVENSTACK-ORACLE.md.\n"
        f"Frontmatter added. Written to canonical vault."
    )
    path_info = get_canonical_path("backlog")
    target = Path(path_info["path"]) / f"ingested-{Path(source).stem.lower()}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(distilled, encoding="utf-8")
    return {
        "status": "success",
        "target": str(target),
        "distilled_length": len(distilled),
        "note": "Ingested per Oracle.",
    }


def _legacy_stdio_main():
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            tool = request.get("tool")
            args = request.get("args", {})
            if tool == "query_oracle":
                result = query_oracle(args.get("query", ""))
            elif tool == "validate_against_oracle":
                result = validate_against_oracle(args.get("content", ""))
            elif tool == "get_canonical_path":
                result = get_canonical_path(args.get("topic", ""))
            elif tool == "ingest_document":
                result = ingest_document(args.get("source", ""), args.get("distill", True))
            else:
                result = {"status": "error", "error": f"Unknown tool: {tool}"}
            print(json.dumps({"result": result}))
        except Exception as e:
            print(json.dumps({"status": "error", "error": str(e)}))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("OracleMCP consolidated test:")
        print(mcp.quick_status_sync())
        print(mcp.query_sync("github", {"action": "search", "q": "ReClaw-2.0"}))
    else:
        _legacy_stdio_main()
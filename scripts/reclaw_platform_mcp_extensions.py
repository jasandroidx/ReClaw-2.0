"""Extra reclaw-platform MCP tools (Tier A–D operator surface).

Registered onto the main FastMCP instance via register_extensions().
Keeps reclaw_platform_mcp_server.py readable while expanding operator tools.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def register_extensions(
    mcp: Any,
    *,
    root: Path,
    vault: Path,
    gateway: str,
    openclaw: str,
    ts_ip: str,
    curl: Callable[..., str],
    curl_json: Callable[..., str],
    safe_path: Callable[[Path, str], Path],
    safe_session_id: Callable[[str], str | None],
    run: Callable[..., str],
    project_sitrep: Callable[[], str],
    pipeline_status: Callable[[], str],
) -> None:
    """Attach Tier A–D tools to an existing FastMCP server."""

    def _jload(raw: str) -> dict | list | None:
        if not raw or raw.startswith("request failed:"):
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _read_public_url() -> str:
        p = root / "data" / "mcp_public_url.txt"
        if not p.is_file():
            return ""
        return p.read_text(encoding="utf-8", errors="replace").strip()

    def _git_summary(path: Path) -> dict:
        if not path.is_dir() or not (path / ".git").exists():
            return {"path": str(path), "error": "not a git repo"}
        br = run(["git", "status", "-sb"], cwd=path)
        head = run(["git", "rev-parse", "--short", "HEAD"], cwd=path)
        dirty = bool(
            run(["git", "status", "--porcelain"], cwd=path).strip()
            and not run(["git", "status", "--porcelain"], cwd=path).startswith("error:")
        )
        # recompute dirty cleanly
        por = run(["git", "status", "--porcelain"], cwd=path)
        dirty = bool(por.strip()) and not por.startswith("error:")
        return {
            "path": str(path),
            "branch_line": br.splitlines()[0] if br and not br.startswith("error:") else br,
            "head": head.strip() if head and not head.startswith("error:") else head,
            "dirty": dirty,
        }

    def _openclaw_config() -> dict:
        cfg = Path(os.environ.get("OPENCLAW_CONFIG", "/root/.openclaw/openclaw.json"))
        if not cfg.is_file():
            return {"error": f"missing {cfg}"}
        try:
            return json.loads(cfg.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError as e:
            return {"error": f"invalid json: {e}"}

    def _ollama_models() -> dict:
        raw = curl("http://127.0.0.1:11434/api/tags", timeout=10)
        data = _jload(raw)
        if not isinstance(data, dict):
            return {"status": "down", "detail": raw[:300]}
        names = [m.get("name") for m in (data.get("models") or []) if isinstance(m, dict)]
        return {"status": "up", "models": names, "count": len(names)}

    def _county_status() -> dict | None:
        raw = curl(f"{gateway}/county-queue/status")
        data = _jload(raw)
        return data if isinstance(data, dict) else None

    def _refuse_unless_confirm(confirm: bool, action: str) -> str | None:
        if confirm is True:
            return None
        return (
            f"REFUSED: '{action}' is gated. "
            "Only call with confirm=true when the human explicitly asked for this action. "
            "Do not auto-run from Automations or digests."
        )

    # --- Tier A -------------------------------------------------------------

    @mcp.tool()
    def connector_status() -> str:
        """MCP connector liveness: public URL, local health, tunnel unit, security notes."""
        public = _read_public_url()
        host_file = root / "data" / "mcp_tunnel_host.txt"
        tunnel_host = (
            host_file.read_text(encoding="utf-8", errors="replace").strip()
            if host_file.is_file()
            else ""
        )
        # NEVER curl this process's own :8100 from inside a tool call — single-worker
        # streamable-http deadlocks (health/tool hang until client timeout).
        bridge = run(["systemctl", "is-active", "reclaw-mcp-bridge"]).strip()
        tunnel = run(["systemctl", "is-active", "reclaw-mcp-tunnel"]).strip()
        listen = run(
            ["bash", "-lc", "ss -tlnp 2>/dev/null | grep -F ':8100' | head -1 || true"]
        ).strip()
        local = {
            "status": "ok" if bridge == "active" and ":8100" in listen else "degraded",
            "service": "reclaw-platform",
            "transport": "streamable-http",
            "port": 8100,
            "probed_via": "systemd+ss (no self-HTTP — avoids deadlock)",
            "bridge_unit": bridge,
            "listen_line": listen[:200] if listen else None,
        }
        public_health = ""
        public_code = ""
        if public:
            base = public[:-4] if public.endswith("/mcp") else public.rstrip("/")
            # Public cloudflared path is external — OK to probe (not this process socket).
            proc = subprocess.run(
                ["curl", "-sS", "-o", "/tmp/mcp_pub_health.json", "-w", "%{http_code}", "-m", "8", f"{base}/health"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            public_code = (proc.stdout or "").strip()
            try:
                public_health = Path("/tmp/mcp_pub_health.json").read_text(encoding="utf-8")[:300]
            except OSError:
                public_health = ""

        out = {
            "as_of": _now(),
            "local_health": local,
            "public_url": public or None,
            "public_url_ends_with_mcp": public.endswith("/mcp") if public else False,
            "public_health_http": public_code or None,
            "public_health_body": public_health or None,
            "tunnel_host_file": tunnel_host or None,
            "systemd": {
                "reclaw-mcp-bridge": bridge,
                "reclaw-mcp-tunnel": tunnel,
            },
            "tailscale_mcp": f"http://{ts_ip}:8100/mcp",
            "tailscale_health": f"http://{ts_ip}:8100/health",
            "security": {
                "http_auth": "none — treat public URL as secret",
                "prefer": "Tailscale when possible",
                "tunnel_type": "disabled - public plane is Tailscale Funnel (stable)",
                "upgrade_path": "Named Cloudflare tunnel + optional Access/OAuth for auth",
            },
            "tool_surface": "reclaw-platform (primary) + stacked Firecrawl/GitHub/Chrome DevTools",
            "note": "If a client health-checks 127.0.0.1:8100 during a long tool call, use a short timeout; prefer tool results over nested self-probes.",
        }
        return json.dumps(out, indent=2)

    @mcp.tool()
    def public_mcp_url() -> str:
        """Return the current public SuperGrok connector URL (from data/mcp_public_url.txt)."""
        url = _read_public_url()
        if not url:
            return "missing data/mcp_public_url.txt — set Funnel URL in data/mcp_public_url.txt"
        note = ""
        if not url.endswith("/mcp"):
            note = "\nWARNING: URL should end with /mcp"
        return f"{url}{note}\n\nSOT file: {root / 'data' / 'mcp_public_url.txt'}\nRefresh: Funnel SOT stable; do not use quick tunnel"


    @mcp.tool()
    def dashboard_status() -> str:
        """Read live fortress dashboard status.json (network, queue, services)."""
        path = root / "dashboard" / "status.json"
        if not path.is_file():
            # generate once
            try:
                py = str(root / ".venv" / "bin" / "python")
                subprocess.run(
                    [py, str(root / "scripts" / "write_fortress_dashboard_status.py")],
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except Exception as e:
                return f"status.json missing and refresh failed: {e}"
        if not path.is_file():
            return "status.json missing — run scripts/write_fortress_dashboard_status.py"
        return path.read_text(encoding="utf-8", errors="replace")[:12000]

    @mcp.tool()
    def county_queue_card(max_chars: int = 8000) -> str:
        """Read-only county queue review card: status JSON + Obsidian review note preview."""
        st = _county_status()
        if not st:
            raw = curl(f"{gateway}/county-queue/status")
            return f"county-queue/status failed:\n{raw[:1500]}"

        pending = st.get("pending_review") or {}
        obs = (pending.get("obsidian_file") or "").strip()
        body = ""
        path_used = ""
        if obs:
            # prefer Rural Data/
            candidates = [
                vault / "Rural Data" / obs,
                vault / "Rural Data" / Path(obs).name,
                vault / obs,
            ]
            for c in candidates:
                try:
                    if c.is_file() and str(c.resolve()).startswith(str(vault.resolve())):
                        body = c.read_text(encoding="utf-8", errors="replace")[:max_chars]
                        path_used = str(c.relative_to(vault))
                        break
                except (OSError, ValueError):
                    continue

        lines = [
            "# County queue review card (READ-ONLY)",
            f"As of: {_now()}",
            "",
            f"- Queue status: **{st.get('queue_status')}**",
            f"- Cursor: {st.get('cursor')}/{st.get('total_counties')}",
            f"- Current: {(st.get('current_county') or {}).get('name') or st.get('current_county')}",
            f"- Approved: {st.get('approved_count')} · Rejected: {st.get('rejected_count')} · Remaining: {st.get('remaining')}",
            "",
        ]
        if pending:
            lines += [
                "## Pending review",
                f"- County: **{pending.get('county')}**",
                f"- Status: {pending.get('status')}",
                f"- Risk: {pending.get('risk_score')} · Flags: {pending.get('flag_count')}",
                f"- Top finding: {pending.get('top_finding')}",
                f"- Recommendation: {pending.get('recommendation')}",
                f"- Package: {pending.get('package_id')} · Session: {pending.get('session_id')}",
                f"- Review file: {pending.get('obsidian_file')}",
                "",
                "**Human gate required** — use county_queue_approve / county_queue_reject only with explicit human OK.",
                "",
            ]
        else:
            lines.append("_No pending review card._\n")

        if body:
            lines += [f"## Review note preview (`{path_used}`)", "", body]
        elif obs:
            lines.append(f"_Review note not found for `{obs}` under vault._")

        return "\n".join(lines)

    @mcp.tool()
    def morning_digest(write_to_vault: bool = False) -> str:
        """Phase B morning operator digest: sitrep + queue + top actions + suggested (not executed) auto-actions.

        write_to_vault=True writes Ravenstack/ops/morning-digest-YYYY-MM-DD.md (explicit intent only).
        """
        sitrep = project_sitrep()
        pipe_raw = pipeline_status()
        pipe = _jload(pipe_raw) if not pipe_raw.startswith("request failed") else None
        # pipeline_status returns JSON string
        if pipe is None and pipe_raw.strip().startswith("{"):
            pipe = _jload(pipe_raw)

        cq = (pipe or {}).get("county_queue") if isinstance(pipe, dict) else None
        if not cq:
            cq = _county_status() or {}

        ollama = _ollama_models()
        oc_cfg = _openclaw_config()
        primary = (
            ((oc_cfg.get("agents") or {}).get("defaults") or {}).get("model") or {}
        )
        if isinstance(primary, dict):
            primary_model = primary.get("primary") or "?"
        else:
            primary_model = str(primary)

        # gaps from sitrep text
        gaps: list[str] = []
        in_gaps = False
        for line in sitrep.splitlines():
            if line.startswith("## 14. Blockers") or line.startswith("## 14."):
                in_gaps = True
                continue
            if in_gaps and line.startswith("## "):
                break
            if in_gaps and line.strip().startswith("-"):
                gaps.append(line.strip().lstrip("- ").strip())

        suggested: list[dict] = []
        qstatus = (cq or {}).get("status") or (cq or {}).get("queue_status")
        if qstatus == "awaiting_approval" or (cq or {}).get("pending_review"):
            county = ((cq or {}).get("pending_review") or {}).get("county") or (cq or {}).get("current") or "?"
            suggested.append(
                {
                    "action": f"Review and approve/reject {county} county queue card",
                    "why": "Queue is blocked on human gate; revenue/content loop stalled",
                    "risk": "medium — publish decision; use gated tools only with explicit OK",
                    "tool": "county_queue_card → county_queue_approve|reject(confirm=true)",
                }
            )
        if any("dirty" in g.lower() for g in gaps):
            suggested.append(
                {
                    "action": "Commit or park dirty ReClaw/vault git work",
                    "why": "Dirty trees hide real signals and risk lost work",
                    "risk": "low — git hygiene",
                    "tool": "git_vault_status",
                }
            )
        suggested.append(
            {
                "action": "Keep SuperGrok connector URL current after tunnel restarts",
                "why": "Quick tunnels can rotate hostnames",
                "risk": "low",
                "tool": "public_mcp_url / connector_status",
            }
        )

        actions = []
        for g in gaps[:3]:
            actions.append(g)
        if not actions:
            actions = ["Stack clear — run pipeline or queue next county when ready"]

        # Overall from sitrep header
        overall = "unknown"
        for line in sitrep.splitlines()[:5]:
            if "Overall:" in line:
                overall = line.split("Overall:", 1)[-1].strip()
                break

        digest = "\n".join(
            [
                f"# SuperGrok Morning Digest — {_today()}",
                f"**As of:** {_now()} UTC",
                f"**Overall:** {overall}",
                "",
                "## 1. Executive",
                "Live fortress digest via reclaw-platform MCP. Report-only; nothing approved or published by this tool.",
                "",
                "## 2. Stack (from sitrep)",
                "See full sitrep sections 2–8 below (Docker, API, OpenClaw, Tailscale, MCP, Ollama, dashboard).",
                f"- OpenClaw primary model: `{primary_model}`",
                f"- Ollama: {ollama.get('status')} · models: {', '.join(ollama.get('models') or []) or 'n/a'}",
                "",
                "## 3. County queue",
                f"- Status: **{qstatus or (cq or {}).get('queue_status') or '?'}**",
                f"- Cursor: {(cq or {}).get('cursor')}/{(cq or {}).get('total_counties') or (cq or {}).get('total_counties')}",
                f"- Pending: {json.dumps((cq or {}).get('pending_review') or {}, indent=2)[:1200]}",
                "",
                "**Human gate required** if status is awaiting_approval.",
                "",
                "## 4. Gaps",
            ]
            + ([f"- {g}" for g in gaps] if gaps else ["- None reported"])
            + [
                "",
                "## 5. Top actions (for you)",
            ]
            + [f"{i}. {a}" for i, a in enumerate(actions, 1)]
            + [
                "",
                "## 6. SUGGESTED auto-actions (NOT executed)",
                "_Do not run these without explicit human OK._",
                "",
            ]
        )
        for s in suggested:
            digest += (
                f"- **{s['action']}**\n"
                f"  - Why: {s['why']}\n"
                f"  - Risk: {s['risk']}\n"
                f"  - How: `{s['tool']}`\n"
            )

        digest += "\n---\n\n## Full sitrep\n\n" + sitrep

        written = ""
        if write_to_vault:
            rel = f"Ravenstack/ops/morning-digest-{_today()}.md"
            p = safe_path(vault, rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            header = (
                "---\n"
                f"title: Morning Digest {_today()}\n"
                f"generated_at: {_now()}\n"
                "source: reclaw-platform.morning_digest\n"
                "tags: [ops, digest, supergrok]\n"
                "---\n\n"
            )
            p.write_text(header + digest, encoding="utf-8")
            written = f"\n\n_Wrote vault note: `{rel}`_"

        # Best-effort live dashboard refresh (same-origin status.json)
        try:
            py = str(root / ".venv" / "bin" / "python")
            subprocess.run(
                [py, str(root / "scripts" / "write_fortress_dashboard_status.py")],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception:
            pass

        return digest + written

    # --- Tier B -------------------------------------------------------------

    @mcp.tool()
    def list_packages(limit: int = 8) -> str:
        """List recent ContentPackages from the ReClaw API."""
        limit = max(1, min(int(limit), 50))
        return curl_json("GET", f"/packages?limit={limit}")

    @mcp.tool()
    def package_summary(package_id: str = "") -> str:
        """Summarize one package by id (default: latest). Distilled fields only."""
        raw = curl(f"{gateway}/packages?limit=20")
        data = _jload(raw)
        if not isinstance(data, dict):
            return raw[:1500]
        packages = data.get("packages") or []
        if not packages:
            return "no packages"
        pid = (package_id or "").strip()
        chosen = None
        if pid:
            for p in packages:
                if p.get("id") == pid:
                    chosen = p
                    break
            if not chosen:
                return f"package not in recent list: {pid}"
        else:
            chosen = packages[0]
        return json.dumps(chosen, indent=2)

    @mcp.tool()
    def openclaw_models() -> str:
        """OpenClaw primary model + agent roster + configured providers (from openclaw.json)."""
        cfg = _openclaw_config()
        if cfg.get("error"):
            return json.dumps(cfg, indent=2)
        agents = cfg.get("agents") or {}
        defaults = agents.get("defaults") or {}
        # list named agents if present
        named = {}
        for k, v in agents.items():
            if k == "defaults":
                continue
            if isinstance(v, dict):
                named[k] = {
                    "model": v.get("model"),
                    "workspace": v.get("workspace") or v.get("agentDir"),
                }
        providers = ((cfg.get("models") or {}).get("providers") or {})
        provider_summary = {
            name: [m.get("id") for m in (p.get("models") or []) if isinstance(m, dict)]
            for name, p in providers.items()
            if isinstance(p, dict)
        }
        out = {
            "defaults_model": defaults.get("model"),
            "named_agents": named,
            "providers": provider_summary,
            "openclaw_health": _jload(curl(f"{openclaw}/health", timeout=5))
            or curl(f"{openclaw}/health", timeout=5)[:200],
        }
        return json.dumps(out, indent=2)

    @mcp.tool()
    def ollama_models() -> str:
        """List local Ollama models (cost-free routing inventory)."""
        return json.dumps(_ollama_models(), indent=2)

    @mcp.tool()
    def git_vault_status() -> str:
        """Git status for ReClaw repo AND Obsidian vault (dirty flag + HEAD)."""
        out = {
            "as_of": _now(),
            "reclaw_repo": _git_summary(root),
            "obsidian_vault": _git_summary(vault),
        }
        return json.dumps(out, indent=2)

    @mcp.tool()
    def pending_gates() -> str:
        """All human gates: county queue pending + recent session approval counts."""
        cq = _county_status() or {}
        pending_review = cq.get("pending_review")
        sessions_raw = curl(f"{gateway}/sessions?limit=5")
        sessions = _jload(sessions_raw)
        sess_list = []
        if isinstance(sessions, dict):
            for s in sessions.get("sessions") or []:
                sid = s.get("session_id") or s.get("id")
                if not sid:
                    continue
                safe = safe_session_id(str(sid))
                if not safe:
                    continue
                ap_raw = curl(f"{gateway}/sessions/{safe}/approvals")
                ap = _jload(ap_raw)
                if isinstance(ap, dict):
                    sess_list.append(
                        {
                            "session_id": safe,
                            "pending": len(ap.get("pending") or []),
                            "grants": len(ap.get("grants") or []),
                        }
                    )
                else:
                    sess_list.append({"session_id": safe, "approvals": ap_raw[:200]})

        out = {
            "as_of": _now(),
            "county_queue": {
                "status": cq.get("queue_status") or cq.get("status"),
                "cursor": cq.get("cursor"),
                "pending_review": {
                    "county": (pending_review or {}).get("county"),
                    "status": (pending_review or {}).get("status"),
                    "risk_score": (pending_review or {}).get("risk_score"),
                    "flag_count": (pending_review or {}).get("flag_count"),
                    "top_finding": (pending_review or {}).get("top_finding"),
                    "obsidian_file": (pending_review or {}).get("obsidian_file"),
                }
                if pending_review
                else None,
            },
            "recent_session_approvals": sess_list,
            "rule": "Approve/reject only with explicit human intent (confirm=true tools).",
        }
        return json.dumps(out, indent=2)

    @mcp.tool()
    def save_operator_decision(
        decision: str,
        context: str = "",
        tags: str = "ops,decision",
    ) -> str:
        """Write a distilled operator decision note into Ravenstack/ops/decisions/ (vault write)."""
        decision = (decision or "").strip()
        if not decision:
            return "decision text required"
        # sanitize filename slug
        slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", decision.lower())[:60].strip("-") or "decision"
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rel = f"Ravenstack/ops/decisions/{ts}-{slug}.md"
        p = safe_path(vault, rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        body = (
            "---\n"
            f"title: {decision[:120]}\n"
            f"generated_at: {_now()}\n"
            "source: reclaw-platform.save_operator_decision\n"
            f"tags: {tag_list}\n"
            "---\n\n"
            f"# Operator decision\n\n"
            f"**Decision:** {decision}\n\n"
            f"**Context:**\n\n{context or '_none_'}\n"
        )
        p.write_text(body, encoding="utf-8")
        return f"wrote {rel}"

    # --- Tier C (gated) -----------------------------------------------------

    @mcp.tool()
    def county_queue_approve(
        confirm: bool = False,
        granted_by: str = "human:mcp",
        publish_formats: str = "",
    ) -> str:
        """GATE: Approve pending county queue item. confirm=true required. Human must ask explicitly."""
        refused = _refuse_unless_confirm(confirm, "county_queue_approve")
        if refused:
            return refused
        body: dict[str, Any] = {"granted_by": granted_by or "human:mcp"}
        fmts = [x.strip() for x in (publish_formats or "").split(",") if x.strip()]
        if fmts:
            body["publish_formats"] = fmts
        return curl_json("POST", "/county-queue/approve", body=body, timeout=120)

    @mcp.tool()
    def county_queue_reject(reason: str, confirm: bool = False) -> str:
        """GATE: Reject pending county with required reason. confirm=true required.
        Also auto-appends a durable playbook lesson so the next scan improves."""
        refused = _refuse_unless_confirm(confirm, "county_queue_reject")
        if refused:
            return refused
        reason = (reason or "").strip()
        if not reason:
            return "reject reason required (logged for revisit)"
        return curl_json("POST", "/county-queue/reject", body={"reason": reason}, timeout=60)

    @mcp.tool()
    def auditor_playbook_show() -> str:
        """Show living auditor playbook context (truth rules + open mistakes) loaded every scan."""
        try:
            import sys

            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            from tools.auditor_playbook import (
                forbidden_vendor_names,
                load_playbook,
                playbook_context_for_session,
            )

            pb = load_playbook()
            sample = sorted(forbidden_vendor_names())[:25]
            return (
                playbook_context_for_session()
                + "\n\n"
                + json.dumps(
                    {
                        "paths": pb.get("paths"),
                        "load_errors": pb.get("load_errors"),
                        "forbidden_vendors_sample": sample,
                    },
                    indent=2,
                )
            )
        except Exception as exc:  # noqa: BLE001
            return f"auditor_playbook_show failed: {exc}"

    @mcp.tool()
    def log_auditor_lesson(
        lesson_id: str,
        symptom: str,
        root_cause: str,
        content_rule: str,
        county: str = "",
        confirm: bool = False,
    ) -> str:
        """Append a durable auditor lesson (mistakes YAML + lessons log). confirm=true required.
        Use after human feedback or research so agents improve on the next run."""
        refused = _refuse_unless_confirm(confirm, "log_auditor_lesson")
        if refused:
            return refused
        try:
            import sys

            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            from tools.auditor_playbook import log_lesson

            out = log_lesson(
                lesson_id=lesson_id,
                symptom=symptom,
                root_cause=root_cause,
                content_rule=content_rule,
                county_example=county or None,
            )
            return json.dumps(out, indent=2)
        except Exception as exc:  # noqa: BLE001
            return f"log_auditor_lesson failed: {exc}"

    @mcp.tool()
    def county_queue_run_next(confirm: bool = False, force: bool = False) -> str:
        """GATE: Run next county in queue (audit + review card). confirm=true required. Long-running."""
        refused = _refuse_unless_confirm(confirm, "county_queue_run_next")
        if refused:
            return refused
        qs = "force=true" if force else "force=false"
        return curl_json("POST", f"/county-queue/run-next?{qs}", timeout=600)

    @mcp.tool()
    def re_export_package(package_id: str, confirm: bool = False) -> str:
        """GATE: Re-export a ContentPackage to Obsidian by package id. confirm=true required."""
        refused = _refuse_unless_confirm(confirm, "re_export_package")
        if refused:
            return refused
        pid = (package_id or "").strip()
        if not pid or not re.fullmatch(r"[A-Za-z0-9._-]+", pid):
            return "invalid package_id"
        return curl_json("POST", f"/re-export/{pid}", timeout=120)

    @mcp.tool()
    def session_approve_capability(
        session_id: str,
        capability: str,
        confirm: bool = False,
        granted_by: str = "human:mcp",
    ) -> str:
        """GATE: Grant a pending high-risk session capability. confirm=true required."""
        refused = _refuse_unless_confirm(confirm, "session_approve_capability")
        if refused:
            return refused
        sid = safe_session_id(session_id)
        if not sid:
            return "invalid session_id"
        cap = (capability or "").strip()
        if not cap or not re.fullmatch(r"[A-Za-z0-9._-]+", cap):
            return "invalid capability name"
        from urllib.parse import quote

        gb = quote(granted_by or "human:mcp", safe="")
        return curl_json(
            "POST",
            f"/sessions/{sid}/approve?capability={quote(cap, safe='')}&granted_by={gb}",
            timeout=60,
        )

    # --- Tier D hooks -------------------------------------------------------

    def _collect_gap_issues() -> list[dict]:
        sitrep = project_sitrep()
        gaps: list[str] = []
        in_gaps = False
        for line in sitrep.splitlines():
            if "Blockers" in line and line.startswith("##"):
                in_gaps = True
                continue
            if in_gaps and line.startswith("## "):
                break
            if in_gaps and line.strip().startswith("-"):
                gaps.append(line.strip().lstrip("-* ").strip())

        cq = _county_status() or {}
        if cq.get("pending_review"):
            c = (cq["pending_review"] or {}).get("county")
            gaps.append(f"County queue awaiting approval: {c}")

        issues = []
        seen_titles: set[str] = set()
        for g in gaps:
            clean = re.sub(r"\*+", "", g)
            clean = re.sub(r"^(low|medium|high)\s*[·•\-:]+\s*", "", clean, flags=re.I).strip()
            title = (clean[:100] if clean else "ops gap").strip()
            key = title.lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            issues.append(
                {
                    "title": f"[ops] {title}",
                    "body": (
                        f"From live project_sitrep gap:\n\n> {g}\n\n"
                        f"Generated: {_now()}\n"
                        "Source: reclaw-platform file_github_gaps / github_gap_suggestions\n\n"
                        "Labels: needs-triage, ready-for-human"
                    ),
                    "gap": g,
                }
            )
        return issues

    @mcp.tool()
    def github_gap_suggestions() -> str:
        """Map live sitrep gaps to suggested GitHub issue titles (does NOT create issues)."""
        issues = _collect_gap_issues()
        if not issues:
            issues = [
                {
                    "title": "[ops] Routine sitrep — no gaps (placeholder)",
                    "body": "No blockers in latest sitrep.",
                    "gap": None,
                }
            ]
        out = {
            "as_of": _now(),
            "note": "Suggestions only. File with file_github_gaps(confirm=true) after human OK.",
            "suggested_issues": [
                {"title": i["title"], "body_hint": i.get("body", "")[:400], "create": False}
                for i in issues
            ],
            "combo": "file_github_gaps(confirm=true) or GitHub MCP issue_write after explicit ask.",
        }
        return json.dumps(out, indent=2)

    @mcp.tool()
    def file_github_gaps(
        confirm: bool = False,
        repo: str = "jasandroidx/ReClaw-2.0",
        dry_run: bool = False,
        max_issues: int = 5,
    ) -> str:
        """GATE: Create GitHub issues from live sitrep gaps via gh CLI. confirm=true required.

        Skips titles that already match an open issue. dry_run=true previews without creating.
        """
        refused = _refuse_unless_confirm(confirm, "file_github_gaps")
        if refused:
            return refused
        max_issues = max(1, min(int(max_issues or 5), 15))
        repo = (repo or "jasandroidx/ReClaw-2.0").strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            return "invalid repo (use owner/name)"

        issues = _collect_gap_issues()
        if not issues:
            return json.dumps({"created": [], "skipped": [], "note": "no gaps"}, indent=2)

        # open issue titles for dedupe
        list_raw = run(
            ["gh", "issue", "list", "-R", repo, "--state", "open", "--limit", "50", "--json", "number,title"]
        )
        open_titles: list[str] = []
        if list_raw and not list_raw.startswith("error:"):
            try:
                open_titles = [x.get("title") or "" for x in json.loads(list_raw)]
            except json.JSONDecodeError:
                pass

        created = []
        skipped = []
        for issue in issues[:max_issues]:
            title = issue["title"]
            if any(title.lower() == (t or "").lower() or title.lower() in (t or "").lower() for t in open_titles):
                skipped.append({"title": title, "reason": "similar open issue exists"})
                continue
            if dry_run:
                created.append({"title": title, "dry_run": True})
                continue
            proc = subprocess.run(
                [
                    "gh",
                    "issue",
                    "create",
                    "-R",
                    repo,
                    "--title",
                    title,
                    "--body",
                    issue.get("body") or title,
                    "--label",
                    "needs-triage",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode != 0:
                # labels may not exist — retry without label
                proc = subprocess.run(
                    [
                        "gh",
                        "issue",
                        "create",
                        "-R",
                        repo,
                        "--title",
                        title,
                        "--body",
                        issue.get("body") or title,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            if proc.returncode == 0:
                created.append({"title": title, "url": (proc.stdout or "").strip()})
            else:
                skipped.append(
                    {
                        "title": title,
                        "reason": (proc.stderr or proc.stdout or "gh failed")[:300],
                    }
                )

        return json.dumps(
            {
                "as_of": _now(),
                "repo": repo,
                "dry_run": dry_run,
                "created": created,
                "skipped": skipped,
            },
            indent=2,
        )

    @mcp.tool()
    def skill_stack_map() -> str:
        """How reclaw-platform stacks with Firecrawl, Chrome DevTools, Superpowers, CF docs, GitHub."""
        return """# Ravenstack skill / connector stack map

## Primary fortress connector
- **reclaw-platform** — live Hetzner truth: sitrep, queue, vault, pipeline, gates

## Stacked power packs (same chat, do not merge into platform)
| Pack | Use for | Auth |
|------|---------|------|
| Firecrawl | County site search/scrape/map (Tier-3 harvest) | OAuth / API key |
| Chrome DevTools | Dashboard/Control UI, CWV, console | Local Chrome (installed headless) |
| GitHub | Issues/PRs from gaps | OAuth (jasandroidx) |
| cloudflare-docs | Tunnel/Workers design | None |
| CF API MCPs | Account control | OAuth — optional, off by default |
| Superpowers | brainstorm → plan → TDD → verify workflows | None |
| Gmail/Calendar | Comms/schedule | OAuth when connected |

## Daily loop
1. morning_digest or project_sitrep
2. county_queue_card if awaiting_approval
3. Human decision → gated approve/reject
4. Firecrawl if research refresh needed
5. github_gap_suggestions → file_github_gaps(confirm=true) only if human asks

## Security
- Public MCP URL = secret (no HTTP auth yet)
- Prefer Tailscale MCP
- confirm=true gates for mutations
"""

"""
ObsidianWriter — final mile for every content package.

Writes a clean, human + LLM friendly .md file directly into your Obsidian vault
(or a staging folder that you later sync).

Design goals:
- Pure functions + one class. No side effects except the write.
- Deterministic filenames: YYYY-MM-DD-{slug}.md
- Rich frontmatter so you can query in Dataview / Bases / plugins.
- Sections that map directly to faceless channel workflow (stats, red flags, angles).
- Easy for Scriptwriter agent (later) to consume the same .md or its JSON sibling.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .config import get_settings
from .handoff import ContentPackage, ResearchPackage, AnalysisPackage


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text.lower())
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text or "untitled"


def render_table(rows: list[dict[str, Any]], headers: list[str] | None = None) -> str:
    """Very small markdown table renderer. No extra deps."""
    if not rows:
        return "_No data._\n"
    if headers is None:
        headers = list(rows[0].keys())
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for r in rows:
        line = "| " + " | ".join(str(r.get(h, "")) for h in headers) + " |"
        lines.append(line)
    return "\n".join(lines) + "\n"


class ObsidianWriter:
    def __init__(self, settings: Any | None = None):
        self.settings = settings or get_settings()
        self.target_dir = self.settings.effective_obsidian_path
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def write_package(self, package: ContentPackage, dry_run: bool | None = None) -> Path:
        """
        Write the full package as a beautiful .md + sidecar .json.
        Returns the path to the .md file.
        """
        dry = self.settings.write_dry_run if dry_run is None else dry_run
        date_str = package.generated_at.strftime("%Y-%m-%d")
        slug = slugify(f"{package.county}-{package.primary_area}")
        filename = f"{date_str}-{slug}.md"
        md_path = self.target_dir / filename
        json_path = md_path.with_suffix(".json")

        frontmatter = package.to_obsidian_frontmatter()
        body = self._render_body(package)

        content = "---\n" + yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True) + "---\n\n" + body

        if dry:
            print(f"[DRY] Would write {md_path}")
            print(f"[DRY] Would write {json_path}")
            return md_path

        md_path.write_text(content, encoding="utf-8")
        json_path.write_text(package.model_dump_json(indent=2), encoding="utf-8")

        # Also write a tiny pointer for the latest run (useful for dashboard / Discord bot later)
        latest = self.target_dir / "_latest.md"
        latest.write_text(f"Last generated: {package.id}\nSee: [[{filename}]]\n", encoding="utf-8")

        package.obsidian_filename = filename
        return md_path

    def _render_body(self, pkg: ContentPackage) -> str:
        r: ResearchPackage = pkg.research
        a: AnalysisPackage = pkg.analysis

        lines: list[str] = []
        lines.append(f"# {pkg.county} County — {pkg.primary_area} Rural Data Package\n")
        lines.append(f"**Generated:** {pkg.generated_at.isoformat()}  |  **Risk Score:** {a.overall_risk_score}/10\n")
        lines.append(f"Research: `{r.id}`  •  Analysis: `{a.id}`\n\n")

        # Quick stats block (great for voiceover / thumbnail)
        lines.append("## Key Stats\n")
        stats = pkg.key_stats or {}
        if stats:
            for k, v in stats.items():
                lines.append(f"- **{k}:** {v}")
        else:
            lines.append(f"- Properties analyzed: {r.total_properties}")
            if r.median_assessed:
                lines.append(f"- Median assessed value: ${r.median_assessed:,}")
            lines.append(f"- Red flags surfaced: {len(a.red_flags)}")
        lines.append("")

        # Research summary
        lines.append("## Research Summary\n")
        lines.append(r.summary.strip() + "\n\n")

        # Budget snapshot
        if r.budgets:
            lines.append("## Budget Snapshot\n")
            for b in r.budgets:
                lines.append(f"**{b.entity} — FY{b.fiscal_year}**\n")
                if b.total_revenue:
                    lines.append(f"- Revenue: ${b.total_revenue:,}")
                if b.total_expenditures:
                    lines.append(f"- Expenditures: ${b.total_expenditures:,}")
                if b.surplus_deficit is not None:
                    sign = "+" if b.surplus_deficit >= 0 else ""
                    lines.append(f"- Net: {sign}${b.surplus_deficit:,}")
                if b.major_funds:
                    lines.append("- Major funds:")
                    for fund, amt in b.major_funds.items():
                        lines.append(f"  - {fund}: ${amt:,}")
                if b.notes:
                    lines.append(f"\n_Notes: {b.notes}_\n")
            lines.append("")

        # Property highlights (sample)
        if r.property_records:
            lines.append("## Sample Property Records\n")
            sample = [
                {
                    "Parcel": p.parcel_id,
                    "Address": p.address,
                    "Acres": p.land_acres or "?",
                    "Assessed": f"${p.assessed_value:,}" if p.assessed_value else "?",
                    "Class": p.property_class or "",
                }
                for p in r.property_records[:8]
            ]
            lines.append(render_table(sample, ["Parcel", "Address", "Acres", "Assessed", "Class"]))
            lines.append("_Full list in sidecar JSON. Use for maps / deeper research._\n\n")

        # Salaries (if any)
        if r.salaries:
            lines.append("## Public Payroll Highlights\n")
            sal_rows = [
                {
                    "Dept": s.department,
                    "Position": s.position,
                    "Avg": f"${s.avg_salary:,}" if s.avg_salary else "",
                    "Range": f"${s.min_salary or 0:,}–${s.max_salary or 0:,}" if s.min_salary or s.max_salary else "",
                }
                for s in r.salaries[:6]
            ]
            lines.append(render_table(sal_rows))
            lines.append("")

        # Insights
        lines.append("## Insights (Rural Reality)\n")
        for ins in a.insights:
            lines.append(f"### {ins.title}\n")
            lines.append(ins.detail + "\n")
            if ins.supporting_numbers:
                lines.append("Supporting: " + ", ".join(ins.supporting_numbers) + "\n")
            if ins.suggested_angle:
                lines.append(f"> **Content angle:** {ins.suggested_angle}\n")
            lines.append("")
        lines.append("")

        # Red Flags — this is gold for the channel
        if a.red_flags:
            lines.append("## Red Flags\n")
            for flag in sorted(a.red_flags, key=lambda f: {"critical":0,"high":1,"medium":2,"low":3}.get(f.severity, 9)):
                sev = flag.severity.upper()
                lines.append(f"- **[{sev}] {flag.category}:** {flag.description}")
                lines.append(f"  - Evidence: {flag.evidence}")
                if flag.recommended_action:
                    lines.append(f"  - Action: {flag.recommended_action}")
            lines.append("")

        # Budget implications
        if a.budget_implications:
            lines.append("## Budget Implications\n")
            for imp in a.budget_implications:
                lines.append(f"- {imp}")
            lines.append("")

        # Content angles (ready for next agent)
        if a.content_angles:
            lines.append("## Content Angles (Faceless Channel)\n")
            for i, angle in enumerate(a.content_angles, 1):
                lines.append(f"{i}. {angle}")
            lines.append("")

        # Video title ideas
        if pkg.video_title_ideas:
            lines.append("## Suggested Video Titles\n")
            for t in pkg.video_title_ideas:
                lines.append(f"- {t}")
            lines.append("")

        # Sources & provenance
        lines.append("## Sources & Provenance\n")
        for src in r.sources:
            if src.url:
                lines.append(f"- [{src.kind}] {src.url} ({src.fetched_at.date()})")
            else:
                lines.append(f"- [{src.kind}] {src.note or 'seed data'}")
        lines.append("")

        lines.append("## Package IDs\n")
        lines.append(f"- Research: `{r.id}`\n- Analysis: `{a.id}`\n- Package: `{pkg.id}`\n")

        lines.append("\n---\n*ReClaw 2.0 — Rural Data for the Faceless Channel. Generated for Obsidian.*\n")
        return "\n".join(lines)

# HANDOFF.md — ReClaw 2.0 JSON Contract

All communication between Researcher, Analyst, Orchestrator, and the Gateway uses the models defined in `core/handoff.py`.

## The Three Packages

1. **ResearchPackage** (Researcher → Analyst / Orchestrator)
   - county, primary_area, fetched_at, sources[]
   - property_records[] (parcel_id, address, acres, assessed_value, class, notes, provenance)
   - budgets[] (entity, year, revenue, expenditures, deficit, major_funds, sources)
   - salaries[]
   - summary (plain English, 3-6 sentences, no interpretation)
   - raw_excerpts (optional notable lines from source pages)

2. **AnalysisPackage** (Analyst → Orchestrator)
   - research_id (links back)
   - insights[] (category, title, detail, supporting_numbers[], suggested_angle)
   - red_flags[] (severity, category, description, evidence, recommended_action)
   - budget_implications[]
   - content_angles[] (ready-to-record video ideas)
   - overall_risk_score (0-10)
   - summary

3. **ContentStudioOutput** (Content Studio → Orchestrator)
   - short_scripts[] (hook, script, CTA, engagement_score, provenance)
   - video_title_ideas[]
   - scripts_pruned count

4. **ContentPackage** (Orchestrator final)
   - research + analysis embedded
   - short_scripts[], approval_status (`pending_approval` default)
   - key_stats, video_title_ideas
   - tags, obsidian_filename
   - to_obsidian_frontmatter() helper for clean YAML

5. **CompliancePackage** (Silent Auditor, optional)
   - red_flags[], overall_risk_score — merged into Content Studio when present

## On Disk (inside a session)

```
data/sessions/<session-id>/
  handoffs/
    researcher.json       # full ResearchPackage
    analyst.json          # full AnalysisPackage
    content_studio.json   # ContentStudioOutput
    silent_auditor.json   # CompliancePackage (optional)
  approvals/...
  logs/...
  soul/...
```

The final package is also written to `data/runs/<ts>_<pkg-id>.json` and the Obsidian sidecar.

This strict contract is what makes the swarm reliable, replayable, and easy to extend with new agents (just consume the previous package type and emit the next).

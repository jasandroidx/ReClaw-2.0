# Continuous improvement — auditor agents

## Problem
Chat memory and RAG do **not** change what detectors emit. Human rejects only help if lessons are written to disk and enforced on the next run.

## Pattern (how others do it)
Self-improving agent systems (2025–2026) share one loop:

1. **Act** — run the task  
2. **Score** — human reject/approve, rubric, or tests  
3. **Persist** — write lessons to a durable file (`learnings.md`, `AGENTS.md`, rule YAML)  
4. **Inject** — load those files at the start of every future run  

References in spirit: AGENTS.md compound loops, learnings.md feedback stores, “lesson loops” that update rules without weight training.

## ReClaw implementation

| Step | Mechanism |
|------|-----------|
| Load | `tools.auditor_playbook.load_playbook()` — truth, mistakes, source map, blueprint, strategy |
| Filter | `filter_flags_by_truth()` after detectors in `red_flag_engine` + `silent_auditor` |
| Reject → lesson | `CountyQueue.reject` → `log_lesson()` → mistakes + `auditor_lessons_log.yaml` |
| Manual lesson | `python tools/auditor_playbook.py --log-id ...` or MCP `log_auditor_lesson` |
| Show rules | `python tools/auditor_playbook.py --show` or MCP `auditor_playbook_show` |

## Living files

- `data/content_truth_rules.yaml` — hard kills, publish gate, heat rank  
- `data/audit_pipeline_mistakes.yaml` — open + fixed mistakes  
- `data/auditor_lessons_log.yaml` — timestamped log (auto on reject)  
- `data/public_source_map.yaml` — where receipts live  
- `data/indiana_public_finance_blueprint.yaml` — hard_kill lists + recipes  

## Operator loop

1. Review card in Obsidian  
2. **Reject with a specific reason** (training signal) or approve  
3. If reject: lesson is already on disk; fix code/rules if needed  
4. `POST /county-queue/refresh` or run-next after unfreeze  

## Tests

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_auditor_playbook.py -q
```

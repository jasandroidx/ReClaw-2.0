# County Video Shorts — Tool Map

## Live primaries (always cite these)

| Need | Tool path |
|------|-----------|
| Named salaries | Chrome DevTools → gateway.ifionline.org Employee Compensation |
| Special investigations | SBOA API + `in.gov/sboa/WebReports/{id}I.pdf` |
| Certified budgets | curl DLGF `{County}-*-Budget-Order.pdf` + text extract |
| Wage scales | County document center PDF + tesseract OCR |
| Census / ranks | Firecrawl scrape QuickFacts, Census Reporter, stats.indiana.edu |
| History | Firecrawl + Bioguide + in.gov/ibc + IMH |

## Fortress helpers

| Need | Path / tool |
|------|-------------|
| SBOA ingest helper | `cd /root/ReClaw-2.0 && PYTHONPATH=. .venv/bin/python tools/sboa_ingest.py {County}` |
| Outbox publish | `outbox-publish /root/outbox/FILE.md --title "…"` |
| Vault SOT narrative | `Ravenstack/skills/county-video-package.md` |
| Legal language | `ReClaw-2.0/docs/SILENT-AUDITOR-WORKFLOW.md` |

## Reject

OpenPayrolls, Salary.com, Glassdoor, wrong-state domains, AFR rollup “vendors”, draft SBOA.

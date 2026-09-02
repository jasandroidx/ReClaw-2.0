#!/usr/bin/env bash
# Discover SBOA audit PDFs for one county or worklist batch.
set -euo pipefail
cd /root/ReClaw-2.0
export $(grep -v '^#' .env 2>/dev/null | xargs) || true
COUNTY="${1:-Spencer}"
LIMIT="${2:-}"

if [[ -n "$LIMIT" ]]; then
  PYTHONPATH=. .venv/bin/python -c "
import yaml
from tools.sboa_ingest import ingest_sboa_county
wl = yaml.safe_load(open('data/indiana_county_worklist.yaml'))['counties']
for c in wl[:int('$LIMIT')]:
    m = ingest_sboa_county(c['name'])
    print(c['name'], len(m.get('pdfs', [])), 'pdfs', len(m.get('findings', [])), 'findings')
"
else
  PYTHONPATH=. .venv/bin/python -c "
from tools.sboa_ingest import ingest_sboa_county
import json
m = ingest_sboa_county('$COUNTY')
print(json.dumps({'county': '$COUNTY', 'pdfs': len(m.get('pdfs', [])), 'findings': len(m.get('findings', []))}))
"
fi
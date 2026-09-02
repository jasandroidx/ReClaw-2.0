#!/usr/bin/env bash
# Top Indiana counties by peer-outlier score — feeds "Top 5 anomaly" shorts strategy.
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHONPATH=. .venv/bin/python -c "
from tools.county_peer_audit import rank_counties_for_content
for i, c in enumerate(rank_counties_for_content(top_n=10), 1):
    print(f\"#{i} {c['name']:12} score={c['outlier_score']:.1f}  budget/cap=\${c['budget_per_capita']:,.0f}  disb/cap=\${c['disb_per_capita']:,.0f}\")
"
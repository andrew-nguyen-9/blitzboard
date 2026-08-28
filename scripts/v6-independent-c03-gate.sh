#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${C03_PYTHON:-python3}"

cd "$repo_root"
"$python_bin" scripts/v6BenchPortfolioPrototype.py --output .orchestrator-v6/prep/C03-synthetic-results.json
PYTHONPATH=engine "$python_bin" -m pytest \
  engine/tests/test_v6BenchPortfolio_adversarial.py \
  engine/tests/test_v6BenchShape_adversarial.py -q -rxX

#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
common_git_dir="$(git -C "$repo_root" rev-parse --git-common-dir)"
source_root="$(cd "$(dirname "$common_git_dir")" && pwd)"
vitest="$source_root/frontend/node_modules/.bin/vitest"
python="$source_root/pipeline/.venv/bin/python"

(cd "$repo_root/frontend" && "$vitest" run lib/v6BenchBaseline.adversarial.test.ts)
(cd "$repo_root" && PYTHONPATH=engine "$python" -m pytest engine/tests/test_v6_waiver_baseline_adversarial.py -rxX)

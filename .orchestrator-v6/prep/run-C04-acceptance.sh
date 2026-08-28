#!/usr/bin/env bash
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root/frontend"
npx vitest run \
  lib/v6DraftIntegration.adversarial.test.ts \
  lib/v6DraftTrace.contract.test.ts \
  lib/v6Explanation.contract.test.ts

cd "$repo_root"
git diff --check

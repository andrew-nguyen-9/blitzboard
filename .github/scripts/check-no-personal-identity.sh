#!/usr/bin/env bash
# Regression guard for D18 / v2.0.5: fails if personal identity reappears in
# product-facing surfaces. Internal docs/ deliberately discuss the
# "Andrew-ification" removal and the "Smores" seed history, so they are excluded.
set -euo pipefail

# Run from the repo root regardless of the caller's working directory.
cd "$(dirname "$0")/../.."

PATTERN='andrew|smores|my league|my-league'
PATHS=(frontend/app frontend/components frontend/lib frontend/scripts db README.md)

if grep -rniE "$PATTERN" "${PATHS[@]}" 2>/dev/null; then
  echo "✗ personal identity found in product-facing surfaces (see matches above)."
  echo "  Keep the product generic (D18); use 'Example Superflex League' / 'SUPERFLEX_ROSTER'."
  exit 1
fi

echo "✓ no personal identity in product-facing surfaces"

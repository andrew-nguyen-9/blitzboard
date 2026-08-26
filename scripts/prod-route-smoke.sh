#!/usr/bin/env bash
set -euo pipefail

base_url="${1:-http://127.0.0.1:3100}"
body="$(mktemp)"
trap 'rm -f "$body"' EXIT

check_route() {
  local route="$1" marker="$2"
  curl --fail --silent --show-error --max-time 30 "$base_url$route" --output "$body"
  if ! grep --fixed-strings --quiet "$marker" "$body"; then
    echo "FAIL $route: missing marker '$marker'" >&2
    return 1
  fi
  echo "PASS $route: $marker"
}

check_route "/" "Open the draft board"
check_route "/players" "Player Explorer"
check_route "/draft" "Draft Board"

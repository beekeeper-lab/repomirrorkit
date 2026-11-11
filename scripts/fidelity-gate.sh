#!/usr/bin/env bash
# Harvest every checked-in fixture and fail if any misses the fidelity gates.
# Usage: scripts/fidelity-gate.sh   (run from the repo root; used by CI)
set -euo pipefail

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
status=0

for dir in tests/fixtures/sample-projects/*/; do
  name="$(basename "$dir")"
  repo="$work/$name"
  cp -r "$dir" "$repo"
  git -C "$repo" init -q
  git -C "$repo" add -A
  git -C "$repo" -c user.name=ci -c user.email=ci@example.com commit -qm fixture
  if uv run requirements-harvester harvest --repo "$repo" --out "$work/out-$name" \
      --no-llm --no-fail-on-gaps --fail-on-fidelity --log-level error >/dev/null 2>&1; then
    echo "PASS  $name"
  else
    echo "FAIL  $name (see $work/out-$name/reports/coverage.md)"
    status=1
  fi
done
exit "$status"

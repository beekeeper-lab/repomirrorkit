#!/usr/bin/env bash
# Fail if any tracked file contains a credential-shaped string.
# Usage: scripts/check-no-secrets.sh   (run from the repo root; used by CI)
# Known test fakes carry the word EXAMPLE and are allowed.
set -euo pipefail

pattern='(sk-ant-[A-Za-z0-9_-]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|AIza[0-9A-Za-z_-]{30,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|BEGIN [A-Z ]*PRIVATE KEY-----[A-Za-z0-9+/]{20,})'

hits="$(git grep -nIE "$pattern" -- . ':!uv.lock' | grep -v 'EXAMPLE' || true)"
if [ -n "$hits" ]; then
  echo "Possible secrets in tracked files:" >&2
  echo "$hits" | sed -E 's/(.{80}).*/\1.../' >&2
  exit 1
fi

# Key files must never be tracked.
bad="$(git ls-files | grep -E '(^|/)(providers\.env|\.env|[^/]*\.pem|id_rsa[^/]*)$' || true)"
if [ -n "$bad" ]; then
  echo "Key/env files are tracked: $bad" >&2
  exit 1
fi
echo "No secrets detected in tracked files."

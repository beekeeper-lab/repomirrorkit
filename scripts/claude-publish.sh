#!/usr/bin/env bash
#
# claude-publish.sh — Push kit submodule first, then parent repo.
#
# Usage:
#   scripts/claude-publish.sh              # push both kit and parent
#   scripts/claude-publish.sh --kit-only   # push kit submodule only
#
# Never use this to push TO claude-kit from a consumer repo.
# Only foundry pushes to claude-kit.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KIT_DIR="${REPO_ROOT}/.claude/kit"

KIT_ONLY=false

for arg in "$@"; do
  case "$arg" in
    --kit-only) KIT_ONLY=true ;;
    *) echo "Unknown argument: $arg"; exit 1 ;;
  esac
done

log() { echo "[publish] $*"; }

# --- Push kit submodule ---
if [ -d "$KIT_DIR/.git" ] || [ -f "$KIT_DIR/.git" ]; then
  log "Pushing kit submodule..."
  git -C "$KIT_DIR" push
  log "Kit submodule pushed."
else
  log "Kit submodule not found at ${KIT_DIR}. Skipping."
fi

if $KIT_ONLY; then
  log "Done (--kit-only)."
  exit 0
fi

# --- Push parent repo ---
log "Pushing parent repo..."
git -C "$REPO_ROOT" push
log "Parent repo pushed."

log "Done."

#!/usr/bin/env bash
# claude-sync.sh — Thin wrapper that delegates to the kit's sync script.
exec "$(git rev-parse --show-toplevel)/.claude/shared/scripts/claude-sync.sh" "$@"

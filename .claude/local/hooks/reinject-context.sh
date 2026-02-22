#!/usr/bin/env bash
#
# reinject-context.sh — Re-inject available commands/skills after context compaction
#
# Fired by Claude Code's SessionStart hook with matcher "compact".
# Reads hook input JSON from stdin, checks source == "compact",
# then scans .claude/commands/ and .claude/skills/ to output a
# summary that gets injected into Claude's context.
#
set -euo pipefail

# Read hook input from stdin
INPUT=$(cat)
SOURCE=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('source',''))" 2>/dev/null || echo "")

# Only run after compaction
if [ "$SOURCE" != "compact" ]; then
  exit 0
fi

# Find repo root (where .claude/ lives)
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
CLAUDE_DIR="${REPO_ROOT}/.claude"

# Collect commands (strip .md extension, skip internal/)
COMMANDS=()
if [ -d "${CLAUDE_DIR}/commands" ]; then
  for f in "${CLAUDE_DIR}/commands"/*.md; do
    [ -f "$f" ] || continue
    name=$(basename "$f" .md)
    COMMANDS+=("$name")
  done
fi

# Collect skills (directory names, skip internal/)
SKILLS=()
if [ -d "${CLAUDE_DIR}/skills" ]; then
  for d in "${CLAUDE_DIR}/skills"/*/; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    [ "$name" = "internal" ] && continue
    SKILLS+=("$name")
  done
fi

# Output the context re-injection
cat << 'HEADER'
--- CONTEXT RE-INJECTED AFTER COMPACTION ---

The following commands and skills are available in this project.
Use the Skill tool to invoke them (e.g., /command-name).
HEADER

echo ""
echo "Available commands (invoke with /name):"
for cmd in "${COMMANDS[@]}"; do
  echo "  - /${cmd}"
done

echo ""
echo "Available skills:"
for skill in "${SKILLS[@]}"; do
  echo "  - ${skill}"
done

echo ""
echo "See CLAUDE.md for project conventions. See ai/personas/ for persona definitions."
echo "--- END RE-INJECTED CONTEXT ---"

#!/usr/bin/env bash
#
# claude-kit-check.sh — Verify Claude-Kit integration health
#
# Checks submodule presence, symlink wiring, layout detection,
# legacy nesting, and stale remotes. Optional --fix mode for
# auto-repair of common issues.
#
# Usage:
#   scripts/claude-kit-check.sh              # diagnostic (PASS/FAIL)
#   scripts/claude-kit-check.sh --fix        # auto-repair issues
#   scripts/claude-kit-check.sh --fix --dry-run  # preview fixes
#   scripts/claude-kit-check.sh --quiet      # exit code only
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_DIR="${REPO_ROOT}/.claude"
KIT_DIR="${CLAUDE_DIR}/kit"
LOCAL_DIR="${CLAUDE_DIR}/local"
SYNC_SCRIPT="${REPO_ROOT}/scripts/claude-sync.sh"

FIX=false
DRY_RUN=false
QUIET=false
FAILURES=0

for arg in "$@"; do
  case "$arg" in
    --fix)     FIX=true ;;
    --dry-run) DRY_RUN=true ;;
    --quiet)   QUIET=true ;;
    --help|-h)
      echo "Usage: scripts/claude-kit-check.sh [--fix] [--dry-run] [--quiet]"
      echo ""
      echo "  --fix       Auto-repair common issues"
      echo "  --dry-run   Preview fixes without applying (requires --fix)"
      echo "  --quiet     Suppress output, exit code only (0=pass, 1=fail)"
      exit 0
      ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

log()  { $QUIET || echo "[check] $*"; }
pass() { $QUIET || echo "[check] PASS: $*"; }
fail() { $QUIET || echo "[check] FAIL: $*" >&2; FAILURES=$((FAILURES + 1)); }
info() { $QUIET || echo "[check]   -> $*"; }

# ---------------------------------------------------------------------------
# Check 1: Submodule presence
# ---------------------------------------------------------------------------
check_submodule() {
  log "Checking submodule presence..."

  local stage_mode
  stage_mode="$(git -C "$REPO_ROOT" ls-files --stage .claude/kit 2>/dev/null | awk '{print $1}' || true)"

  if [ "$stage_mode" = "160000" ]; then
    pass "Submodule .claude/kit is gitlink mode 160000"
  else
    fail "Submodule .claude/kit not found or wrong mode (got: '${stage_mode:-empty}')"
    if $FIX; then
      info "Fix: initializing submodule..."
      if $DRY_RUN; then
        info "(dry-run) Would run: git submodule update --init --recursive"
      else
        git -C "$REPO_ROOT" submodule update --init --recursive
        info "Submodule initialized"
      fi
    else
      info "To fix: git submodule update --init --recursive"
    fi
  fi

  # Also verify the submodule working tree exists
  if [ -d "$KIT_DIR" ] && [ -e "${KIT_DIR}/.git" ]; then
    pass "Submodule working tree is populated"
  else
    fail "Submodule working tree is empty or missing"
    if $FIX; then
      info "Fix: initializing submodule..."
      if $DRY_RUN; then
        info "(dry-run) Would run: git submodule update --init --recursive"
      else
        git -C "$REPO_ROOT" submodule update --init --recursive
        info "Submodule initialized"
      fi
    else
      info "To fix: git submodule update --init --recursive"
    fi
  fi
}

# ---------------------------------------------------------------------------
# Check 2: .claude/local exists
# ---------------------------------------------------------------------------
check_local_dir() {
  log "Checking .claude/local..."

  if [ -d "$LOCAL_DIR" ]; then
    pass ".claude/local exists"
  else
    fail ".claude/local directory is missing"
    info "To fix: create .claude/local/ with appropriate subdirectories"
  fi
}

# ---------------------------------------------------------------------------
# Check 3: Layout detection and symlink wiring
# ---------------------------------------------------------------------------
detect_layout() {
  if [ -d "${KIT_DIR}/commands" ] || [ -d "${KIT_DIR}/agents" ]; then
    echo "kit-root"
  elif [ -d "${KIT_DIR}/.claude/shared" ]; then
    echo "nested"
  else
    echo "unknown"
  fi
}

check_symlink() {
  local path="$1"
  local description="$2"

  if [ -L "$path" ]; then
    if [ -e "$path" ]; then
      pass "${description} ($(readlink "$path"))"
    else
      fail "${description} is a broken symlink -> $(readlink "$path")"
      return 1
    fi
  elif [ -e "$path" ]; then
    # Exists but not a symlink — for directories that contain symlinks, this is OK
    pass "${description} (directory with symlinks)"
  else
    fail "${description} is missing"
    return 1
  fi
  return 0
}

check_dir_has_symlinks() {
  local dir="$1"
  local description="$2"

  if [ ! -d "$dir" ]; then
    fail "${description} directory missing"
    return 1
  fi

  local total=0
  local symlinks=0
  local broken=0
  for entry in "$dir"/*; do
    [ -e "$entry" ] || [ -L "$entry" ] || continue
    total=$((total + 1))
    if [ -L "$entry" ]; then
      symlinks=$((symlinks + 1))
      if [ ! -e "$entry" ]; then
        broken=$((broken + 1))
        $QUIET || echo "[check] FAIL:   broken symlink: $(basename "$entry") -> $(readlink "$entry")" >&2
        FAILURES=$((FAILURES + 1))
      fi
    fi
  done

  if [ "$total" -eq 0 ]; then
    fail "${description} is empty"
    return 1
  elif [ "$broken" -gt 0 ]; then
    fail "${description} has ${broken} broken symlink(s) out of ${total} entries"
    return 1
  else
    pass "${description} (${symlinks} symlinks, ${total} total entries)"
    return 0
  fi
}

check_symlinks() {
  local layout
  layout="$(detect_layout)"
  log "Detected layout: ${layout}"

  if [ "$layout" = "unknown" ]; then
    fail "Cannot detect kit layout — .claude/kit may not be initialized"
    if $FIX; then
      info "Fix: initializing submodule and re-syncing..."
      if $DRY_RUN; then
        info "(dry-run) Would run: git submodule update --init --recursive && scripts/claude-sync.sh"
      else
        git -C "$REPO_ROOT" submodule update --init --recursive
        "$SYNC_SCRIPT"
        info "Submodule initialized and symlinks synced"
      fi
    else
      info "To fix: git submodule update --init --recursive && scripts/claude-sync.sh"
    fi
    return
  fi

  local wiring_ok=true

  if [ "$layout" = "nested" ]; then
    log "Verifying nested layout symlinks..."

    # Top-level shared symlink
    check_symlink "${CLAUDE_DIR}/shared" ".claude/shared -> kit/.claude/shared" || wiring_ok=false

    # settings.json
    check_symlink "${CLAUDE_DIR}/settings.json" ".claude/settings.json" || wiring_ok=false

    # Asset directories (should be real dirs containing symlinks)
    for asset in agents commands hooks skills; do
      check_dir_has_symlinks "${CLAUDE_DIR}/${asset}" ".claude/${asset}" || wiring_ok=false
    done

  elif [ "$layout" = "kit-root" ]; then
    log "Verifying kit-root layout symlinks..."

    for asset in agents commands hooks skills; do
      check_symlink "${CLAUDE_DIR}/${asset}" ".claude/${asset} -> kit/${asset}" || wiring_ok=false
    done

    check_symlink "${CLAUDE_DIR}/settings.json" ".claude/settings.json" || wiring_ok=false
  fi

  if ! $wiring_ok && $FIX; then
    info "Fix: re-running sync script to rewire symlinks..."
    if $DRY_RUN; then
      info "(dry-run) Would run: scripts/claude-sync.sh"
    else
      "$SYNC_SCRIPT"
      info "Symlinks re-synced"
    fi
  elif ! $wiring_ok; then
    info "To fix: scripts/claude-sync.sh"
  fi
}

# ---------------------------------------------------------------------------
# Check 4: Legacy .claude/.claude nesting
# ---------------------------------------------------------------------------
check_legacy_nesting() {
  log "Checking for legacy .claude/.claude nesting..."

  if [ -e "${CLAUDE_DIR}/.claude" ]; then
    fail "Legacy .claude/.claude exists"

    local is_tracked
    is_tracked="$(git -C "$REPO_ROOT" ls-files --error-unmatch .claude/.claude 2>/dev/null && echo "yes" || echo "no")"

    if $FIX; then
      if [ "$is_tracked" = "yes" ]; then
        info "Fix: removing tracked .claude/.claude..."
        if $DRY_RUN; then
          info "(dry-run) Would run: git rm -r .claude/.claude"
        else
          git -C "$REPO_ROOT" rm -r .claude/.claude
          info "Removed tracked .claude/.claude"
        fi
      else
        info "Fix: removing untracked .claude/.claude..."
        if $DRY_RUN; then
          info "(dry-run) Would run: rm -rf .claude/.claude"
        else
          rm -rf "${CLAUDE_DIR}/.claude"
          info "Removed .claude/.claude"
        fi
      fi
    else
      if [ "$is_tracked" = "yes" ]; then
        info "To fix: git rm -r .claude/.claude"
      else
        info "To fix: rm -rf .claude/.claude"
      fi
    fi
  else
    pass "No legacy .claude/.claude nesting"
  fi
}

# ---------------------------------------------------------------------------
# Check 5: Stale claude-kit remote
# ---------------------------------------------------------------------------
check_stale_remote() {
  log "Checking for stale claude-kit remote..."

  if git -C "$REPO_ROOT" remote | grep -qx 'claude-kit'; then
    fail "Stale 'claude-kit' remote exists (leftover from subtree setup)"

    if $FIX; then
      info "Fix: removing stale remote..."
      if $DRY_RUN; then
        info "(dry-run) Would run: git remote remove claude-kit"
      else
        git -C "$REPO_ROOT" remote remove claude-kit
        info "Removed claude-kit remote"
      fi
    else
      info "To fix: git remote remove claude-kit"
    fi
  else
    pass "No stale claude-kit remote"
  fi
}

# ---------------------------------------------------------------------------
# Check 6: Broken symlinks
# ---------------------------------------------------------------------------
check_broken_symlinks() {
  log "Checking for broken symlinks in .claude/..."

  local broken
  broken="$(find "$CLAUDE_DIR" -type l ! -exec test -e {} \; -print 2>/dev/null || true)"

  if [ -n "$broken" ]; then
    fail "Broken symlinks found:"
    while IFS= read -r link; do
      info "  ${link} -> $(readlink "$link")"
    done <<< "$broken"

    if $FIX; then
      info "Fix: re-running sync script..."
      if $DRY_RUN; then
        info "(dry-run) Would run: scripts/claude-sync.sh"
      else
        "$SYNC_SCRIPT"
        info "Symlinks re-synced"
      fi
    else
      info "To fix: scripts/claude-sync.sh"
    fi
  else
    pass "No broken symlinks in .claude/"
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
log "Claude-Kit Integration Health Check"
log "Repo: ${REPO_ROOT}"
log ""

check_submodule
check_local_dir
check_symlinks
check_legacy_nesting
check_stale_remote
check_broken_symlinks

log ""
if [ "$FAILURES" -eq 0 ]; then
  log "=== ALL CHECKS PASSED ==="
  exit 0
else
  log "=== ${FAILURES} CHECK(S) FAILED ==="
  if ! $FIX; then
    log "Run with --fix to auto-repair, or --fix --dry-run to preview fixes."
  fi
  exit 1
fi

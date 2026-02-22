# BEAN-039: Claude-Kit Health Check

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-039 |
| **Status** | In Progress |
| **Priority** | Medium |
| **Created** | 2026-02-22 |
| **Started** | 2026-02-22 04:12 |
| **Completed** | — |
| **Duration** | — |
| **Owner** | team-lead |
| **Category** | Infra |

## Problem Statement

After clone, pull, submodule update, or worktree creation, there is no automated way to verify that the Claude-Kit three-layer integration (kit submodule, local overrides, generated symlinks) is correctly wired. Problems like missing submodule init, broken symlinks, legacy `.claude/.claude` nesting, or stale `claude-kit` remotes from old subtree setups can silently break agent/command/skill discovery. Currently verification requires running a manual checklist of 10+ commands and interpreting the output.

## Goal

A standalone `scripts/claude-kit-check.sh` script that verifies Claude-Kit integration health with clear PASS/FAIL output and an optional `--fix` mode that auto-repairs common issues. The script is also callable from `/validate-repo` so all repo health checks live in one place.

## Scope

### In Scope
- Standalone bash script `scripts/claude-kit-check.sh` with diagnostic output
- Layout detection: nested (`kit/.claude/shared/`) vs kit-root (`kit/{agents,commands,...}`)
- Verification checks: submodule presence (gitlink mode 160000), `.claude/local` existence, symlink wiring for detected layout, no legacy `.claude/.claude`, no stale `claude-kit` remote
- `--fix` flag: auto-init submodule, rewire broken symlinks (delegates to `claude-sync.sh`), remove stale `claude-kit` remote, remove legacy `.claude/.claude` (only if tracked)
- `--dry-run` flag for fix mode (show what would change without changing)
- Integration into `/validate-repo` command as a Claude-Kit check step
- Clear PASS/FAIL summary with "next commands to fix" guidance for any failures

### Out of Scope
- Worktree creation or management (the post-checkout hook already handles this)
- Modifying `claude-sync.sh` itself (the check script calls it, doesn't replace it)
- CI pipeline integration (no CI exists yet)
- Checking the *contents* of kit assets (only checking that symlinks resolve correctly)

## Acceptance Criteria

- [ ] `scripts/claude-kit-check.sh` exists and is executable
- [ ] Running it with no flags produces a PASS/FAIL summary for: submodule presence, symlink wiring, legacy nesting, stale remotes
- [ ] Script auto-detects nested vs kit-root layout and validates accordingly
- [ ] `--fix` mode initializes submodule if missing, runs `claude-sync.sh` if symlinks are broken, removes stale `claude-kit` remote if present, removes legacy `.claude/.claude` if tracked
- [ ] `--fix --dry-run` previews fixes without applying them
- [ ] Script exits 0 on all-pass, exits 1 on any failure (useful for scripting)
- [ ] `/validate-repo` command references the Claude-Kit check as part of its validation steps
- [ ] No broken symlinks after running `--fix` on a repo with a correctly initialized submodule
- [ ] All tests pass
- [ ] Lint clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Create claude-kit-check.sh | developer | — | Done |
| 2 | Integrate into /validate-repo | developer | 1 | Done |
| 3 | Tech-QA Verification | tech-qa | 1, 2 | Pending |

> Skipped: BA (default), Architect (default)

## Notes

- Complements `scripts/claude-sync.sh` which handles symlink creation; this script handles verification and repair
- The `--fix` mode for symlink repair should delegate to `claude-sync.sh` rather than reimplementing symlink logic
- Consider making the check script callable with a `--quiet` flag for use in hooks/scripts (exit code only, no output)

## Trello

| Field | Value |
|-------|-------|
| **Source** | Manual |

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Create claude-kit-check.sh | developer | 1m | 1,138,159 | 491 | $1.92 |
| 2 | Integrate into /validate-repo | developer | 1m | 610,265 | 486 | $1.02 |
| 3 | Tech-QA Verification | tech-qa | — | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | — |
| **Total Duration** | — |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |
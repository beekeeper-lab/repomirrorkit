# Task 01: Create claude-kit-check.sh

| Field | Value |
|-------|-------|
| **Task** | 01 |
| **Owner** | developer |
| **Depends On** | — |
| **Status** | Done |
| **Started** | 2026-02-22 04:13 |
| **Completed** | 2026-02-22 04:14 |
| **Duration** | 1m |

## Goal

Create `scripts/claude-kit-check.sh` — a standalone bash script that verifies Claude-Kit integration health with PASS/FAIL output and optional `--fix` / `--dry-run` modes.

## Inputs

- `scripts/claude-sync.sh` — existing sync script (reference for layout detection and symlink patterns)
- `.gitmodules` — submodule configuration
- `.claude/` directory structure — verification targets

## Deliverables

- `scripts/claude-kit-check.sh` (new, executable)

## Acceptance Criteria

- [ ] Script exists at `scripts/claude-kit-check.sh` and is executable (`chmod +x`)
- [ ] Running with no flags prints PASS/FAIL for: submodule presence, `.claude/local` existence, symlink wiring, legacy `.claude/.claude` nesting, stale `claude-kit` remote
- [ ] Auto-detects nested (`kit/.claude/shared/`) vs kit-root (`kit/{agents,...}`) layout
- [ ] For nested layout: verifies `.claude/shared` symlink, per-asset symlinks in agents/commands/hooks/skills, `settings.json` symlink
- [ ] For kit-root layout: verifies top-level directory symlinks into `kit/`
- [ ] `--fix` mode: inits submodule if missing, runs `claude-sync.sh` if symlinks broken, removes stale `claude-kit` remote, removes legacy `.claude/.claude` if git-tracked
- [ ] `--fix --dry-run` shows what would be fixed without changing anything
- [ ] `--quiet` flag suppresses output (exit code only)
- [ ] Exits 0 on all checks passing, exits 1 on any failure
- [ ] Uses `set -euo pipefail` and follows project shell conventions (consistent with `claude-sync.sh`)
- [ ] No broken symlinks introduced

## Definition of Done

Script passes all acceptance criteria when run on the current repo. Both normal and `--fix` paths verified.

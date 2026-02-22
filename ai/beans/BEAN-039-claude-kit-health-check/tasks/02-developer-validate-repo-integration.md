# Task 02: Integrate into /validate-repo

| Field | Value |
|-------|-------|
| **Task** | 02 |
| **Owner** | developer |
| **Depends On** | 01 |
| **Status** | Done |
| **Started** | 2026-02-22 04:14 |
| **Completed** | 2026-02-22 04:15 |
| **Duration** | 1m |

## Goal

Update the `/validate-repo` command to include Claude-Kit integration checks as part of its validation pipeline.

## Inputs

- `.claude/local/commands/validate-repo.md` — existing command definition
- `scripts/claude-kit-check.sh` — health check script from Task 01

## Deliverables

- `.claude/local/commands/validate-repo.md` (edited)

## Acceptance Criteria

- [ ] `/validate-repo` command references Claude-Kit health check as a named check step
- [ ] The check is included at the structural check level (not just full)
- [ ] The `--fix` flag in validate-repo passes through to `claude-kit-check.sh --fix`
- [ ] Documentation in the command file describes the new check

## Definition of Done

`/validate-repo` command file includes the Claude-Kit integration check step with clear documentation.

# BEAN-058 Task 01: Fix Hook Path in `.claude/shared/settings.json`

| Field | Value |
|-------|-------|
| **Owner** | developer |
| **Status** | Done |
| **Started** | 2026-05-01 10:54 |
| **Completed** | 2026-05-01 10:54 |
| **Duration** | < 1m |
| **Depends On** | — |

## Goal

Bring the `telemetry-stamp.py` PostToolUse hook command into the same convention used by `bash_safety.py` (line 18) and `write_safety.py` (line 27): an absolute path anchored at `$CLAUDE_PROJECT_DIR`. After this task, the hook fires successfully regardless of the cwd Claude Code uses when invoking it.

## Inputs

- `.claude/shared/settings.json` — the file to edit (line 38)
- `BEAN-058 bean.md` — Problem Statement and Goal sections
- Existing pattern at `.claude/shared/settings.json:18,27` for bash_safety and write_safety

## Acceptance Criteria

- [ ] Line 38 of `.claude/shared/settings.json` uses `python3 "$CLAUDE_PROJECT_DIR/.claude/shared/hooks/telemetry-stamp.py"` (matching lines 18 and 27)
- [ ] No other hook commands in the file use the broken relative-path pattern (already audited; line 38 is the only offender)
- [ ] Smoke test: editing any bean.md or `_index.md` no longer produces `python3: can't open file ...` error
- [ ] Smoke test: a deliberate Status transition on a test bean correctly stamps the Started timestamp (replacing the `—` sentinel)

## Definition of Done

- The fix is applied to `.claude/shared/settings.json` in the submodule's working tree
- The submodule's working tree change is **not** committed in the submodule itself (would create a SHA divergence from foundry's claude-kit upstream)
- The parent repo does **not** record a submodule SHA bump
- Smoke-test results are recorded in the bean's Notes section
- Foundry PR todo is documented in the bean's Notes section, with the exact one-line change ready to copy into a foundry → claude-kit PR

## Notes

- The bug is a single-line oversight: when `telemetry-stamp.py` was added later than the safety hooks, it didn't pick up the established convention.
- `$CLAUDE_PROJECT_DIR` is set by Claude Code to the absolute project root for hook execution. It's already in use by lines 18 and 27, so its availability is confirmed.
- Persistent fix requires foundry → claude-kit PR; the local fix here is a working-tree-only edit that survives until the next `git submodule update`.

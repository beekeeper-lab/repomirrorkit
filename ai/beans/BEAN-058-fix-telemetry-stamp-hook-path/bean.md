# BEAN-058: Fix `telemetry-stamp` Hook Path Resolution

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-058 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-05-01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | Infra |

## Problem Statement

The `PostToolUse:Edit` hook in `.claude/shared/settings.json` is configured as `python3 .claude/shared/hooks/telemetry-stamp.py` — a **relative** path. When Claude Code fires this hook, it sets the working directory to the edited file's containing directory (or its parent), not to the project root. As a result, `python3` cannot find the script for any edit that does not happen at the project root. The hook's actual purpose — auto-stamping `Started` / `Completed` / `Duration` fields on bean and task files when status transitions are detected — is broken **precisely for the files it is supposed to operate on** (`ai/beans/BEAN-NNN/bean.md`, `ai/beans/BEAN-NNN/tasks/*.md`, `ai/beans/_index.md`).

Reproduced during the backlog-refinement session that filed BEAN-040 through BEAN-057: every single bean.md `Status` change and every `_index.md` edit produced the error:

```
python3: can't open file
'/home/gregg/Nextcloud/workspace/repomirrorkit/ai/beans/.claude/shared/hooks/telemetry-stamp.py':
[Errno 2] No such file or directory
```

The edits themselves landed (PostToolUse cannot undo a tool that has already run), but no telemetry was stamped. Under `/long-run`, this means every bean transition in the autonomous flow will silently fail to record timing data — which is exactly the data the dashboards and `/telemetry-report` rely on.

## Goal

The `telemetry-stamp.py` hook fires successfully on every bean.md, tasks/*.md, and `_index.md` edit, independent of cwd. Bean status transitions reliably stamp the `Started`, `Completed`, and `Duration` fields. No PostToolUse error appears in normal day-to-day editing.

## Scope

### In Scope
- Replace the relative path in the hook command with one that resolves correctly regardless of cwd. Preferred option: `python3 "$CLAUDE_PROJECT_DIR/.claude/shared/hooks/telemetry-stamp.py"` (Claude Code's standard project-root env var). Acceptable fallback: an absolute literal computed at sync time by `scripts/claude-sync.sh`.
- Decide and document the **fix path**, given that `.claude/shared/settings.json` lives in the `claude-kit` submodule and only the foundry project pushes to that submodule:
  - **Option A — Upstream fix:** open a PR in `foundry → claude-kit` to update the hook command. RepoMirrorKit picks up the fix on the next submodule bump.
  - **Option B — Local override:** add a project-local hook entry in `.claude/local/settings.local.json` so the layered `claude-sync.sh` merge resolves the override (shared keeps the bug; local overrides). Useful as a stopgap; still requires Option A eventually.
  - Recommendation: do both — Option B immediately to unbreak this repo, Option A so every downstream consumer benefits.
- Manual smoke test: edit a bean's `Status` field from `Approved` → `In Progress`; verify `Started` is stamped and no hook error appears.
- Update this bean's notes section with the chosen path, PR link (if any), and any sync-script changes required.

### Out of Scope
- Rewriting the `telemetry-stamp.py` script itself (the script is fine; only its invocation is broken)
- Adding new telemetry fields
- Investigating Claude Code's hook-cwd behavior (it's a platform detail; we just need to work with it)
- Touching other hooks in the same settings file (they may have the same bug, but each is its own bean if so)

## Acceptance Criteria

- [ ] Editing any `bean.md`, `tasks/*.md`, or `_index.md` does not produce a PostToolUse hook error
- [ ] Manually transitioning a bean's `Status` from `Approved` to `In Progress` results in the `Started` field being stamped with a timestamp (replacing the `—` sentinel)
- [ ] Manually transitioning a bean's `Status` to `Done` results in `Completed` and `Duration` being stamped
- [ ] If Option B is chosen, the local override is documented in this bean and verified to survive a `claude-sync.sh` run
- [ ] If Option A is chosen, a foundry PR link is recorded in this bean's notes
- [ ] At least one other hook command in `settings.json` is audited for the same bug pattern (and either confirmed safe or filed as a follow-up bean)
- [ ] Lint and existing test suite stay clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- **Discovered during the session that filed BEAN-040 through BEAN-057.** Every status flip during approval surfaced the error.
- The kit/local override boundary is exactly the case the layered claude-kit architecture was designed to handle — this bean is also a useful real-world test of that boundary.
- DevOps / Release Engineer to own; Architect to weigh in on Option A vs B (recommendation: both).
- Cross-repo touchpoint: foundry → claude-kit. Per the project rule "Never push to claude-kit from this repo — only foundry pushes," the foundry PR happens in a separate working tree, not here.
- Other hooks worth checking for the same pattern when this bean runs: any other `command:` strings in `settings.json` that use `.claude/...` relative paths.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 |      |       |          |           |            |

| Metric | Value |
|--------|-------|
| **Total Tasks** | — |
| **Total Duration** | — |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |

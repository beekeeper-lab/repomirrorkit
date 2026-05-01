# BEAN-049: Fix Misleading Pipeline Resume-Skip Branches

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-049 |
| **Status** | Approved |
| **Priority** | Medium |
| **Created** | 2026-05-01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

`HarvestPipeline.run` claims to support `--resume` from a previous incomplete run by skipping stages that have already completed. In practice, the "skip" branch in `pipeline.py` does not actually skip work for stages B/C/F/G: the code logs `stage_skipped_resume` then immediately re-runs the analyzer or report function on the next lines (`pipeline.py:247-249, 273-275, 376-378, 402-404`). This is because intermediate state is not persisted to disk between stages — only the *fact that the stage completed* is checkpointed. So on resume, B and C re-scan, D builds maps from re-scanned input, F regenerates reports, and G regenerates the project folder. The user sees "skipped" log messages while the work runs anyway. The behavior is undocumented and surprising; either resume should actually skip work, or the skip log lines are misleading and should be removed.

## Goal

`--resume` either does what its name implies (genuinely skips completed stages by rehydrating their outputs from disk) or the misleading "skip" log lines are removed and the documentation is updated to be honest about what `--resume` actually does (skip clone-and-checkout only).

## Scope

### In Scope
- Decide between two paths and document the decision in this bean's notes:
  - **Option A: True resume.** Persist each stage's output to disk (e.g. JSON/parquet/pickle in `<out>/state/`), and on resume rehydrate the output instead of re-running. Higher implementation cost; matches user expectation.
  - **Option B: Honest reduced scope.** Keep state checkpointing for stage A only (the slow network operation) and drop the `is_stage_done` checks for B–G. Update help text and docstrings to say "resume skips clone if already done; analysis stages always re-run."
- Implement the chosen option
- Update `--help` text, `cli.py` docstrings, and any user-facing log messages
- Update existing resume-related tests in `test_state.py` and `test_pipeline.py` to match the new behavior
- Add a test that covers the chosen resume behavior end-to-end against a fixture state directory

### Out of Scope
- Adding incremental analysis (re-run only changed files) — separate concern
- Cross-run output diffing — separate concern
- Changing the state file format unrelated to resume

## Acceptance Criteria

- [ ] A decision (A or B) is recorded in this bean's notes before implementation begins
- [ ] If Option A: each of B, C, D, E, F, G persists its output and reads it back on `--resume`; resume completes in materially less wall time than a fresh run on the same fixture
- [ ] If Option B: the "skip" log messages no longer appear for B–G on resume; the help text accurately describes the behavior
- [ ] No misleading `stage_skipped_resume` log lines for stages that actually re-ran
- [ ] All resume-related tests still pass; new tests cover the chosen behavior
- [ ] Lint, type-check, and pytest all clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Code quality" (2026-05-01)
- Affected lines in `pipeline.py`: 247-249, 273-275, 376-378, 402-404
- Sibling: BEAN-048 (exception handling). Both touch `pipeline.py`. BEAN-048 should land first to reduce diff churn.
- Depends on BEAN-050 (integration test) as safety net for the larger Option A path
- Architect should weigh in on the Option A vs B choice — Option B is the conservative answer; Option A is the right answer if true resume is a real user need

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

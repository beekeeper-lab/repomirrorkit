# BEAN-006: State Management & Resume

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-006 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester pipeline has 6+ stages and may process hundreds of files. If it fails mid-run (network error, timeout, crash), the user must be able to resume from the last completed checkpoint rather than starting over. Without state management, large repositories become impractical to process.

## Goal

A `state.py` module that saves and loads pipeline progress to `state/state.json`, supports `--resume` to skip completed work, and checkpoints after each stage and every N beans (configurable).

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/state.py`
- `StateManager` class with save/load/checkpoint methods
- `state.json` schema: current stage, stage statuses, bean generation progress, timestamps
- Checkpoint after each pipeline stage (A through F)
- Checkpoint every N beans during generation (default: 10, configurable)
- `--resume` support: load state, skip completed stages, continue from last bean
- Never overwrite completed beans on resume
- `state/stages/` directory for optional stage-level intermediate artifacts
- Unit tests for state save/load, resume logic, checkpoint intervals

### Out of Scope
- `--force` flag to overwrite completed beans (v2)
- Stage G (runtime verification) state management
- Pipeline orchestration logic (BEAN-032)
- Distributed/multi-process state coordination

## Acceptance Criteria

- [ ] `StateManager` can save current progress to `state/state.json`
- [ ] `StateManager` can load previous state from `state/state.json`
- [ ] State JSON includes: stage name, stage status (pending/done), bean count, last checkpoint timestamp
- [ ] `--resume` skips stages marked as "done" in state
- [ ] `--resume` continues bean generation from the last checkpoint count
- [ ] Completed beans are never overwritten during resume
- [ ] Checkpoint occurs after each stage completion
- [ ] Checkpoint occurs every N beans (default 10) during generation
- [ ] Missing or corrupt `state.json` starts fresh (no crash)
- [ ] Unit tests cover save, load, resume skip logic, corrupt state handling
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-004 (Harvester Package Setup).
- Reference: Spec sections 4.4 (State outputs), 6 (Pipeline stages — checkpoints), 9.2 (Checkpointing & resume).
- State file is written to `${OUT}/state/state.json` where OUT defaults to the cloned repo's `ai/` directory.
- The state module is consumed by the Pipeline Orchestrator (BEAN-032).

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

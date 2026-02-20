# Task 001: Implement StateManager

| Field | Value |
|-------|-------|
| **Task ID** | 001 |
| **Bean** | BEAN-006 |
| **Status** | In Progress |
| **Owner** | Developer |
| **Priority** | 1 |

## Objective

Implement `StateManager` class in `src/repo_mirror_kit/harvester/state.py` with save/load/checkpoint/resume capabilities.

## Acceptance Criteria

- StateManager saves progress to `state/state.json`
- StateManager loads previous state from `state/state.json`
- State JSON includes: stage name, stage status (pending/done), bean count, timestamp
- Resume skips stages marked as "done"
- Resume continues bean generation from last checkpoint count
- Completed beans never overwritten during resume
- Checkpoint after each stage completion
- Checkpoint every N beans (default 10) during generation
- Missing or corrupt state.json starts fresh

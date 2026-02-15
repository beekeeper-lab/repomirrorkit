# BEAN-032: Pipeline Orchestrator

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-032 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester has 6 pipeline stages (A through F), each with its own module, plus checkpoint management, progress tracking, and error handling. Without a central orchestrator, the CLI and GUI would need to coordinate all these stages manually, duplicating logic and making resume unreliable. A single pipeline orchestrator sequences the stages, manages checkpoints, handles errors, and provides a clean interface for both CLI and GUI consumers.

## Goal

Implement the pipeline orchestrator that sequences Stages A through F, coordinates checkpointing, drives deterministic worklist iteration, handles errors gracefully, and provides an interface usable by both the CLI entry point and the GUI button.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/pipeline.py`
- `HarvestPipeline` class with `run(config: HarvestConfig) -> HarvestResult`
- Stage sequencing: A (clone) → B (inventory + detection) → C (surface extraction) → D (traceability) → E (bean generation) → F (coverage gates)
- Resume support: check state and skip completed stages
- Error handling: catch stage errors, report which stage failed, leave state for resume
- Progress callback interface: emit events for stage start/complete/error/progress (for GUI integration)
- Deterministic worklist iteration per spec section 9.1:
  - Produce ordered worklists for routes, components, endpoints, models
  - Iterate entire worklist — no early exit
  - Record any skipped items with reason
- `HarvestResult` dataclass: success/failure, coverage metrics, gap count, bean count, error details
- Wire CLI entry point to pipeline (connect `cli.py` to `pipeline.py`)
- Unit tests for stage sequencing, resume logic, error handling, callback events

### Out of Scope
- Individual stage implementations (BEAN-008 through BEAN-031)
- Stage G runtime verification (deferred to v2)
- GUI integration (BEAN-033)
- Parallel stage execution

## Acceptance Criteria

- [x] `HarvestPipeline.run()` executes Stages A through F in order
- [x] Each stage completion triggers a state checkpoint
- [x] Resume mode skips completed stages and continues from the last incomplete stage
- [x] Stage errors are caught, reported, and leave the pipeline in a resumable state
- [x] Progress callback fires events: `stage_start`, `stage_complete`, `stage_error`, `progress_update`
- [x] Worklist iteration is deterministic and complete (no items skipped without reason)
- [x] `HarvestResult` contains: success/failure, coverage pass/fail, bean count, gap count
- [x] CLI `harvest` command runs the full pipeline and returns correct exit codes
- [x] `--resume` flag triggers resume mode in the pipeline
- [x] The pipeline handles the case where no surfaces are found (empty repo) gracefully
- [x] Unit tests cover: full pipeline flow (mocked stages), resume from each stage, error in each stage
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Implement HarvestResult dataclass and PipelineEvent callback protocol | Developer | — | Done |
| 2 | Implement HarvestPipeline class with stage sequencing, resume, error handling | Developer | 1 | Done |
| 3 | Wire CLI harvest command to HarvestPipeline | Developer | 2 | Done |
| 4 | Write unit tests for pipeline (full flow, resume, errors, callbacks) | Developer | 2 | Done |
| 5 | Run linting, type checking, and full test suite | Tech-QA | 3,4 | Done |

## Wave Decisions

- **BA**: Skipped — acceptance criteria already precise and testable in the bean definition.
- **Architect**: Skipped — no new component boundaries, API contracts, or technology decisions. The pipeline wires existing modules with well-defined signatures.
- **Developer**: Required — core implementation.
- **Tech-QA**: Required — mandatory for App category beans.

## Notes

- Depends on BEAN-005 (CLI), BEAN-006 (State), BEAN-007 (Logging), BEAN-008 (Stage A), BEAN-009 (Stage B inventory), BEAN-010 (Stage B detection), BEAN-020–BEAN-026 (Stage C), BEAN-027 (Stage D), BEAN-028–BEAN-029 (Stage E), BEAN-030 (Stage F), BEAN-031 (Surface Map).
- Reference: Spec sections 6 (Pipeline stages), 9 (How to avoid quitting early).
- The spec is emphatic: "The tool may not exit successfully unless required coverage artifacts exist." The orchestrator enforces this.
- The progress callback interface is designed so the GUI (BEAN-033) can hook into it for real-time status display.

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

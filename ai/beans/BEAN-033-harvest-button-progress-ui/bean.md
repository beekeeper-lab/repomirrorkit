# BEAN-033: Harvest Button & Progress UI

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-033 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

After a repository is cloned via the existing clone form, the user needs a way to trigger requirements harvesting from the GUI. This requires a "Generate Requirements" button that appears after a successful clone, wires to the harvest pipeline via a background worker, and displays real-time progress — stage status, surface counts, and final results (coverage summary, gap count, bean count).

## Goal

Add a "Generate Requirements" button to the main window that triggers the harvest pipeline on the cloned repository, displays real-time progress via the pipeline's callback interface, and shows a summary of results on completion.

## Scope

### In Scope
- Add "Generate Requirements" `QPushButton` to `MainWindow` (visible/enabled after successful clone)
- Create `src/repo_mirror_kit/workers/harvest_worker.py`:
  - `QThread`-based worker that runs `HarvestPipeline.run()`
  - Emits signals: `stage_changed(str)`, `progress_updated(str)`, `harvest_finished(bool, str)`
  - Connects to pipeline progress callbacks
- UI behavior during harvest:
  - Button disabled while harvesting
  - Status label shows current stage ("Stage B: Inventory & Detection...")
  - Progress details in the log area (surface counts, file counts)
  - Button and clone form disabled during harvest
- UI behavior on completion:
  - Success: status shows summary (N beans generated, coverage X%), button re-enables
  - Failure: status shows error summary, gap count, button re-enables
  - Log area shows full pipeline output
- Construct `HarvestConfig` from the clone form's project path
- Input validation: verify clone completed successfully before allowing harvest
- Unit tests for worker signals, button state management, UI updates

### Out of Scope
- CLI integration (BEAN-005 and BEAN-032 handle that)
- Custom harvest configuration from the GUI (use defaults; CLI for advanced options)
- Results browser (viewing individual beans in the UI)
- Cancel/abort harvest in progress
- Re-harvest or incremental harvest

## Acceptance Criteria

- [x] "Generate Requirements" button appears after a successful clone
- [x] Button is disabled before clone completes and during harvest
- [x] Clicking the button starts the harvest pipeline on the cloned repo path
- [x] Status label updates with current pipeline stage name
- [x] Log area shows real-time progress (surface counts, stage transitions)
- [x] On success: status shows bean count and coverage percentage
- [x] On failure: status shows error message and gap count
- [x] UI remains responsive during harvest (no freezing)
- [x] Button re-enables after harvest completes (success or failure)
- [x] Clone form fields are disabled during harvest
- [x] Unit tests cover: button state, worker signal emission, UI updates
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Create `harvest_worker.py` — QThread worker bridging PipelineCallback to Qt signals | Developer | — | Done |
| 2 | Update `main_window.py` — Add Generate Requirements button, wire harvest worker, manage state | Developer | 1 | Done |
| 3 | Write unit tests for worker signals, button states, UI updates | Tech-QA | 1, 2 | Done |
| 4 | Run quality gates (ruff, mypy, pytest) — 1206/1206 pass | Tech-QA | 3 | Done |

## Notes

- Depends on BEAN-032 (Pipeline Orchestrator) for the pipeline interface and BEAN-002 (Clone Form) for the clone completion signal.
- Follow PySide6 conventions: QThread worker, signals/slots, no UI updates from worker thread.
- The harvest worker pattern mirrors the existing `clone_worker.py` pattern from BEAN-002.
- The button should use the clone form's project directory (`./projects/<project-name>/`) as the harvest target.
- Default `HarvestConfig`: out=`<project>/ai`, fail-on-gaps=true, log-level=info.
- **BA SKIP:** Bean spec already provides detailed acceptance criteria in testable format, clear scope, and defined interfaces. No additional requirements elicitation needed.
- **Architect SKIP:** Architecture prescribed by bean spec — QThread worker following existing clone_worker.py pattern, signal/slot bridge to PipelineCallback, integration into existing MainWindow. No new architectural decisions needed.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Create harvest_worker.py | Developer | — | — | — |
| 2 | Update main_window.py | Developer | — | — | — |
| 3 | Write unit tests | Tech-QA | — | — | — |
| 4 | Quality gates | Tech-QA | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 4 |
| **Total Duration** | — |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |

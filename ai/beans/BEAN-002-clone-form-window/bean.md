# BEAN-002: Clone Form Window

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-002 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The application needs its core user-facing feature: a form where the user enters a project name and a git repository URL, then clicks a Fetch button to clone that repository into a local subfolder. Without this, the application has no functionality beyond an empty window. The clone operation must run on a background thread to keep the UI responsive, and the user needs real-time feedback showing clone progress and any errors.

## Goal

A functional main window where the user can enter a project name and git URL, click Fetch, and have the repository cloned to `./projects/<project-name>/` with real-time status and log output visible in the UI.

## Scope

### In Scope
- `MainWindow` layout with:
  - `QLineEdit` for project name (labeled, required)
  - `QLineEdit` for git URL (labeled, required)
  - `QPushButton` labeled "Fetch"
  - `QLabel` for status text (e.g., "Cloning...", "Done", "Error: ...")
  - Collapsible/expandable `QTextEdit` (read-only) showing git clone output in real time
- Input validation:
  - Project name: non-empty, valid directory name (no path separators or special characters)
  - Git URL: non-empty, basic URL format check (accepts any git-cloneable URL, not restricted to GitHub)
- Clone service (`services/clone_service.py`):
  - Runs `git clone <url> ./projects/<project-name>/` as a subprocess
  - Streams stdout and stderr to the log area in real time
  - Returns success/failure status
- Clone worker (`workers/clone_worker.py`):
  - `QThread`-based worker that runs the clone service off the main thread
  - Emits signals: `output_received(str)`, `clone_finished(bool, str)`
- UI behavior during clone:
  - Fetch button disabled
  - Status label shows "Cloning..."
  - Log area populates with git output line by line
- UI behavior on completion:
  - Success: status shows "Clone complete", button re-enabled
  - Failure: status shows error summary, full error in log area, button re-enabled
- Create `./projects/` directory automatically if it does not exist

### Out of Scope
- User-selectable clone directory (fixed to `./projects/`)
- Authentication for private repositories (SSH keys, tokens)
- Repository management after cloning (pull, push, status)
- Multiple concurrent clones
- Clone history or persistence
- Cancel/abort clone in progress

## Acceptance Criteria

- [ ] User can type a project name and a git URL into labeled text fields
- [ ] Clicking Fetch with empty project name shows an inline validation error and does not start cloning
- [ ] Clicking Fetch with empty URL shows an inline validation error and does not start cloning
- [ ] Clicking Fetch with valid inputs clones the repository to `./projects/<project-name>/`
- [ ] The `./projects/` directory is created automatically if it does not exist
- [ ] The Fetch button is disabled while a clone is in progress
- [ ] The status label updates to "Cloning..." when a clone starts
- [ ] Git clone output appears in the log area in real time (not only after completion)
- [ ] On successful clone, the status label shows "Clone complete" and the button re-enables
- [ ] On failed clone (e.g., invalid URL, network error), the status label shows the error and the button re-enables
- [ ] The UI remains responsive (not frozen) during the clone operation
- [ ] Cloning a URL that is not a GitHub URL works (e.g., GitLab, Bitbucket, any git remote)
- [ ] If the target directory already exists, the clone fails gracefully with an appropriate error message
- [ ] All new code has unit tests; clone worker and service are tested
- [ ] `ruff check` and `mypy` pass with zero errors on all new files

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

> Tasks are populated by the Team Lead during decomposition.
> Task files go in `tasks/` subdirectory.

## Notes

- Depends on BEAN-001 (Project Scaffold) -- the project structure and dependencies must exist first.
- Clone is implemented via `subprocess` calling `git clone`, not via a Python git library (keeps dependencies minimal).
- Follow PySide6 conventions: all UI updates happen on the main thread via signal/slot connections from the worker.
- The collapsible log area should default to expanded during an active clone and retain its state afterward.
- `git` must be available on the system PATH; the app should check for this and show a clear error if git is not found.

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

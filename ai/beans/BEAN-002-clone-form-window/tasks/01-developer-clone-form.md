# Task 01: Implement clone form window

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Status** | Done |
| **Depends On** | — |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |

## Goal

Implement the full clone form UI and backend: form fields, validation, clone service, background worker, and real-time output — satisfying all 15 acceptance criteria from BEAN-002.

## Inputs

- BEAN-002 `bean.md` (scope and acceptance criteria)
- Python stack conventions (`stacks/python/conventions.md`)
- PySide6 conventions (`stacks/pyside6/conventions.md`)
- Existing project scaffold from BEAN-001

## Work

1. Update `src/repo_mirror_kit/views/main_window.py`:
   - Add `QLineEdit` for project name (labeled, required)
   - Add `QLineEdit` for git URL (labeled, required)
   - Add `QPushButton` labeled "Fetch"
   - Add `QLabel` for status text
   - Add collapsible/expandable `QTextEdit` (read-only) for git output log
   - Wire Fetch button to validation + clone logic via signals/slots
   - Disable Fetch button during clone, re-enable on completion

2. Create `src/repo_mirror_kit/services/clone_service.py`:
   - Function to run `git clone <url> ./projects/<project-name>/` as subprocess
   - Stream stdout and stderr line by line
   - Return success/failure
   - Check that `git` is available on PATH
   - Create `./projects/` directory if it does not exist

3. Create `src/repo_mirror_kit/workers/clone_worker.py`:
   - `QThread`-based worker
   - Emits `output_received(str)` for each line of git output
   - Emits `clone_finished(bool, str)` on completion (success/failure + message)

4. Input validation:
   - Project name: non-empty, valid directory name (no path separators or special characters)
   - Git URL: non-empty, basic format check
   - Show inline validation errors

5. Error handling:
   - Target directory already exists → graceful error message
   - Git not found on PATH → clear error message
   - Network error / invalid URL → error in status + log

6. Write unit tests in `tests/unit/`:
   - Test input validation logic
   - Test clone service (mocked subprocess)
   - Test clone worker signals
   - Test MainWindow form behavior

7. Verify: `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Acceptance Criteria

- [ ] All 15 acceptance criteria from BEAN-002 are met
- [ ] `ruff check src/ tests/` reports zero issues
- [ ] `ruff format --check src/ tests/` reports no changes needed
- [ ] `mypy src/` passes strict mode
- [ ] `pytest tests/` passes all tests
- [ ] `from __future__ import annotations` in every new .py module
- [ ] No hardcoded secrets or environment-specific values

## Definition of Done

All files created, all tooling passes, clone form is functional.

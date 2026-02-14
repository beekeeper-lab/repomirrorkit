# BEAN-001: Project Scaffold

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-001 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

RepoMirrorKit has no application code yet — only the AI team scaffolding exists. Before any features can be built, the project needs a properly structured Python + PySide6 skeleton that follows the team's conventions: `uv` for package management, `src/` layout, `hatchling` build backend, and all required tooling (`ruff`, `mypy`, `pytest`). Without this foundation, feature work has no structure to build on.

## Goal

A runnable PySide6 desktop application skeleton that launches an empty main window, with all tooling configured and passing (lint, type-check, tests), so that subsequent beans can add features incrementally.

## Scope

### In Scope
- Initialize the project with `uv` and create a virtual environment
- `pyproject.toml` as the single metadata source with:
  - `hatchling` build backend
  - PySide6 as a runtime dependency
  - Dev dependencies: `ruff`, `mypy`, `pytest`, `pytest-qt`
  - `ruff` lint + format configuration per Python conventions
  - `mypy` strict mode configuration
- `.python-version` pinned to 3.12
- `src/repo_mirror_kit/` package layout with:
  - `__init__.py` (version only)
  - `main.py` (entry point: creates `QApplication`, shows `MainWindow`, runs event loop)
  - `app.py` (application-level setup)
  - `views/` directory with `main_window.py` (empty `QMainWindow` subclass)
  - `services/` directory (empty, for business logic)
  - `workers/` directory (empty, for QThread workers)
  - `models/` directory (empty, for data models)
  - `resources/styles/main.qss` (empty global stylesheet)
- `tests/` directory with `conftest.py` (QApplication fixture) and a smoke test
- `README.md` with project name, description, and setup instructions

### Out of Scope
- Any application features (form fields, clone logic, etc.)
- CI/CD pipeline configuration
- Git repository initialization (handled separately)
- Docker or container configuration
- Application icons or branding

## Acceptance Criteria

- [ ] `uv venv` creates a working virtual environment
- [ ] `uv pip install -e ".[dev]"` installs the package and all dev dependencies without errors
- [ ] `python -m repo_mirror_kit` launches a PySide6 window with the title "RepoMirrorKit" and exits cleanly when closed
- [ ] `ruff check src/ tests/` reports zero issues
- [ ] `ruff format --check src/ tests/` reports no formatting changes needed
- [ ] `mypy src/` passes in strict mode with zero errors
- [ ] `pytest tests/` passes with at least one smoke test (app creates without crashing)
- [ ] Project follows `src/` layout with `from __future__ import annotations` in every module
- [ ] No hardcoded secrets, credentials, or environment-specific values in any file

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

> Tasks are populated by the Team Lead during decomposition.
> Task files go in `tasks/` subdirectory.

## Notes

- This bean must be completed before BEAN-002 (Clone Form Window) can begin.
- Follow Python stack conventions: `uv`, `hatchling`, `ruff`, `mypy` strict, Google-style docstrings.
- Follow PySide6 conventions: signals/slots, layout managers, no fixed pixel positioning.
- Package name: `repo_mirror_kit` (snake_case per Python conventions).

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

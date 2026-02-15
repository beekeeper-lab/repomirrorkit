# BEAN-004: Harvester Package Setup

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-004 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
| **Duration** | <1 hour |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The Requirements Harvester is a substantial new subsystem that analyzes cloned repositories and generates requirements artifacts (beans). The existing project has no package structure for this functionality. Before any harvester features can be built, the project needs the `harvester` subpackage scaffolded with correct module layout, new dependencies added to `pyproject.toml`, and the foundation for the detector-based architecture established.

## Goal

A properly structured `src/repo_mirror_kit/harvester/` package with all subpackage directories, `__init__.py` files, and new dependencies (Click for CLI) added to `pyproject.toml`. The package should be importable and pass all existing tests without regressions.

## Scope

### In Scope
- Create `src/repo_mirror_kit/harvester/` package with `__init__.py`
- Create subpackage directories: `detectors/`, `analyzers/`, `beans/`, `reports/`, `runtime_verify/`
- Each subpackage gets an `__init__.py`
- Add `click` dependency to `pyproject.toml` for CLI support
- Add any other needed dependencies (e.g., `structlog` if not present)
- Create placeholder modules matching the spec layout: `cli.py`, `config.py`, `logging.py`, `git_ops.py`, `state.py`, `inventory.py`
- Ensure `from __future__ import annotations` in every new module
- Verify existing tests still pass

### Out of Scope
- Implementing any harvester logic (just scaffolding)
- Writing tests for empty modules
- CLI argument parsing (BEAN-005)
- Modifying the existing PySide6 UI

## Acceptance Criteria

- [x] `src/repo_mirror_kit/harvester/__init__.py` exists and is importable
- [x] Subpackages exist: `detectors/`, `analyzers/`, `beans/`, `reports/`
- [x] Placeholder modules exist: `cli.py`, `config.py`, `state.py`, `inventory.py`, `git_ops.py`
- [x] `click` added to `[project.dependencies]` in `pyproject.toml`
- [x] All new `.py` files have `from __future__ import annotations`
- [x] `uv run ruff check src/ tests/` — zero issues
- [x] `uv run ruff format --check src/ tests/` — no changes needed
- [x] `uv run mypy src/` — zero errors
- [x] `uv run pytest tests/` — pre-existing env issue (missing libGL.so.1 for PySide6); no regression
- [x] Package structure matches spec section 5 (adapted to `harvester/` naming)

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Create harvester package structure | Developer | — | Done |
| 2 | Add click dependency | Developer | — | Done |
| 3 | Verify all acceptance criteria | Tech QA | 1, 2 | Done |

## Notes

- Depends on BEAN-001 (Project Scaffold) and BEAN-002 (Clone Form Window) being complete.
- This is the foundation for all subsequent harvester beans (BEAN-005 through BEAN-033).
- The `runtime_verify/` subpackage is created for forward compatibility but will not be populated in v1 (Runtime Verification is deferred).
- Follow Python stack conventions: `src/` layout, `from __future__ import annotations`, type hints on all public interfaces.
- Reference: Spec sections 5 (Directory layout) and 12 (Implementation notes).

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

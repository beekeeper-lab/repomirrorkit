# BEAN-016: Python API Detector

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-016 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester needs to detect Python backend API frameworks (FastAPI, Flask) to activate Python-specific endpoint and model analyzers. These frameworks have distinct decorator patterns for route definitions.

## Goal

Implement a Python API detector that identifies FastAPI and Flask projects by examining `pyproject.toml`/`requirements.txt` dependencies, decorator patterns, and framework-specific imports.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/detectors/python_api.py`
- Detect Python backends via:
  - `fastapi` in `pyproject.toml` or `requirements.txt` dependencies
  - `flask` in `pyproject.toml` or `requirements.txt` dependencies
  - FastAPI patterns: `@app.get()`, `@router.post()`, `from fastapi import`
  - Flask patterns: `@app.route()`, `@blueprint.route()`, `from flask import`
  - `pyproject.toml` and `requirements.txt` parsing for dependency detection
- Signal includes which specific framework(s) detected
- Confidence scoring and evidence collection
- Register with detector framework
- Unit tests

### Out of Scope
- Django detection (could be added later)
- Actual endpoint extraction (BEAN-022)
- ASGI/WSGI server detection
- Python version detection

## Acceptance Criteria

- [ ] `PythonApiDetector` implements the `Detector` interface
- [ ] Detects FastAPI via dependency and decorator patterns
- [ ] Detects Flask via dependency and decorator patterns
- [ ] Parses both `pyproject.toml` and `requirements.txt` for dependencies
- [ ] Signal includes the specific framework name(s) detected
- [ ] Confidence scoring based on evidence strength
- [ ] No false positives on non-API Python projects (e.g., CLI tools, libraries)
- [ ] Unit tests cover: FastAPI repo, Flask repo, non-API Python repo
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-010 (Detector Framework).
- Reference: Spec section 2.1 (Python — FastAPI/Flask).

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

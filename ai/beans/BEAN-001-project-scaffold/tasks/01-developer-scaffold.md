# Task 01: Implement project scaffold

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Status** | Done |
| **Depends On** | — |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |

## Goal

Create the complete Python + PySide6 project skeleton per the bean's scope and conventions.

## Inputs

- BEAN-001 `bean.md` (scope and acceptance criteria)
- Python stack conventions (`stacks/python/conventions.md`)
- PySide6 conventions (`stacks/pyside6/conventions.md`)

## Work

1. Create `.python-version` pinned to 3.12
2. Create `pyproject.toml` with hatchling backend, PySide6 dependency, dev deps (ruff, mypy, pytest, pytest-qt), ruff config, mypy strict config
3. Create `src/repo_mirror_kit/__init__.py` with version
4. Create `src/repo_mirror_kit/main.py` entry point (QApplication, MainWindow, event loop)
5. Create `src/repo_mirror_kit/app.py` (application setup)
6. Create `src/repo_mirror_kit/views/__init__.py` and `main_window.py` (empty QMainWindow)
7. Create empty directories: `services/`, `workers/`, `models/` with `__init__.py`
8. Create `src/repo_mirror_kit/resources/styles/main.qss` (empty stylesheet)
9. Create `tests/conftest.py` with QApplication fixture
10. Create `tests/unit/test_smoke.py` with smoke test
11. Initialize with `uv venv && uv pip install -e ".[dev]"`
12. Verify: ruff check, ruff format --check, mypy, pytest all pass
13. Update README.md with setup instructions

## Acceptance Criteria

- [ ] All files from bean scope exist
- [ ] `uv pip install -e ".[dev]"` succeeds
- [ ] `ruff check src/ tests/` reports zero issues
- [ ] `ruff format --check src/ tests/` reports no changes needed
- [ ] `mypy src/` passes strict mode
- [ ] `pytest tests/` passes with smoke test
- [ ] `from __future__ import annotations` in every .py module
- [ ] No hardcoded secrets or environment-specific values

## Definition of Done

All files created, all tooling passes, project is installable and runnable.

# Task 006: Quality gate — ruff, mypy, pytest

| Field | Value |
|-------|-------|
| **Task ID** | 006 |
| **Bean** | BEAN-019 |
| **Owner** | Tech-QA |
| **Status** | Pending |

## Objective
Run all quality gates and verify they pass.

## Acceptance Criteria
- `ruff check src/ tests/` passes with zero errors
- `ruff format --check src/ tests/` passes
- `mypy src/` passes in strict mode
- `pytest tests/` passes with all tests green

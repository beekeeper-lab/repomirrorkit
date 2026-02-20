# Task 003: Tech QA Verification

| Field | Value |
|-------|-------|
| **Owner** | Tech QA |
| **Status** | Pending |
| **Depends On** | Task 001, Task 002 |

## Objective

Run the full quality gate:
- `ruff check src/ tests/`
- `ruff format --check src/ tests/`
- `mypy src/`
- `pytest tests/`

Verify all acceptance criteria from bean.md are covered by tests.

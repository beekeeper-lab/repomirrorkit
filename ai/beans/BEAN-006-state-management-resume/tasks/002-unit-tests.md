# Task 002: Unit Tests for StateManager

| Field | Value |
|-------|-------|
| **Task ID** | 002 |
| **Bean** | BEAN-006 |
| **Status** | Pending |
| **Owner** | Developer |
| **Priority** | 2 |
| **Depends On** | 001 |

## Objective

Write comprehensive unit tests for StateManager covering all acceptance criteria.

## Acceptance Criteria

- Tests for save and load round-trip
- Tests for resume skip logic (completed stages skipped)
- Tests for bean checkpoint intervals
- Tests for corrupt/missing state file handling
- Tests for completed beans protection on resume
- All tests pass with pytest

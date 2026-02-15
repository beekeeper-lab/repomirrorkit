# Task 003: Unit Tests

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Status** | Pending |
| **Depends On** | 002 |

## Objective

Create `tests/unit/test_harvest_logging.py` with unit tests covering:
1. Progress counting (increment, get_snapshot, reset)
2. Log level filtering
3. Heartbeat triggering
4. Report generation
5. No PII/secrets in log output

## Acceptance Criteria

- [ ] Tests for ProgressTracker counting per surface type
- [ ] Tests for log level configuration
- [ ] Tests for heartbeat interval logging
- [ ] Tests for progress report generation
- [ ] All tests pass with pytest

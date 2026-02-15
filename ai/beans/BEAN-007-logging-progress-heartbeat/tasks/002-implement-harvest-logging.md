# Task 002: Implement harvest_logging.py

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Status** | Pending |
| **Depends On** | 001 |

## Objective

Create `src/repo_mirror_kit/harvester/harvest_logging.py` with:
1. Structured logging configuration via structlog (JSON prod, human-readable dev)
2. `configure_logging(log_level)` function
3. `ProgressTracker` class with counters per surface type
4. Heartbeat logging at regular intervals
5. `reports/progress.md` generation
6. Signal-friendly design for GUI integration

## Acceptance Criteria

- [ ] Structured logging via structlog with static event names and keyword args
- [ ] `--log-level` controls verbosity
- [ ] ProgressTracker maintains accurate counters per surface type
- [ ] Heartbeat logs at regular intervals
- [ ] `reports/progress.md` generated with summary
- [ ] No secrets/tokens/PII in logs
- [ ] Progress tracker queryable for current state (GUI integration)

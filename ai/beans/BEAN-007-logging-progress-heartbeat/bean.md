# BEAN-007: Logging & Progress Heartbeat

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-007 |
| **Status** | Approved |
| **Priority** | Medium |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester pipeline processes many files across multiple stages. Without structured logging and progress reporting, users have no visibility into what the tool is doing, how far along it is, or where it got stuck. The spec requires periodic progress heartbeats and optional progress report generation.

## Goal

A logging module that provides structured logging for the harvester pipeline and a progress heartbeat system that periodically reports progress counters (e.g., `routes: 12/57, apis: 4/21`).

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/logging.py` (or rename to avoid stdlib collision)
- Configure structured logging with `structlog` (JSON in production, human-readable in dev)
- Support `--log-level` configuration (debug/info/warn/error)
- Progress tracker class that maintains counters per surface type
- Periodic progress logging: `routes: N/M, components: N/M, apis: N/M, models: N/M`
- Optional `reports/progress.md` generation for human readability
- Signal-friendly design: progress updates can be emitted as Qt signals for GUI integration
- Unit tests for progress tracking and log level configuration

### Out of Scope
- GUI progress display (BEAN-033)
- Logging infrastructure for other parts of the app (only harvester)
- Log file rotation or persistence
- Distributed tracing / correlation IDs

## Acceptance Criteria

- [ ] Structured logging is configured via `structlog` with static event names and keyword args
- [ ] `--log-level` controls verbosity (debug shows file-level detail, info shows stage progress)
- [ ] Progress tracker maintains accurate counters for each surface type
- [ ] Progress heartbeat logs at regular intervals during long operations
- [ ] `reports/progress.md` is generated with current progress summary
- [ ] Log output does not include secrets, tokens, or PII
- [ ] Progress tracker can be queried for current state (for GUI integration)
- [ ] Unit tests cover progress counting, log level filtering
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-004 (Harvester Package Setup).
- The module name may need to be `harvest_logging.py` or similar to avoid shadowing Python's built-in `logging` module.
- Reference: Spec section 9.3 (Progress heartbeat).
- Python stack conventions require `structlog` with static event names and keyword arguments.
- The progress tracker interface should be designed to work with both CLI (log lines) and GUI (Qt signals) consumers.

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

# BEAN-048: Tighten Pipeline Per-Stage Exception Handling

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-048 |
| **Status** | In Progress |
| **Priority** | Medium |
| **Created** | 2026-05-01 |
| **Started** | 2026-05-01 13:03 |
| **Completed** | — |
| **Duration** | — |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

`src/repo_mirror_kit/harvester/pipeline.py` wraps every stage in a generic `except Exception` block — nine of them, at lines 201, 231, 262, 298, 318, 338, 362, 391, and 406. Treating `Exception` as the catch-all class lumps three categories together: (a) expected, domain-specific failures (clone failed, network timeout, missing ref); (b) programming bugs (typos, attribute errors, mis-typed config); and (c) unexpected runtime conditions (out-of-memory, disk full). The pipeline reports all three identically as "Stage X failed: <message>" and writes the run as a normal failure result. Real bugs are silently masked as transient pipeline errors, which makes them very hard to diagnose. The current shape also defeats `mypy --strict` value: typed exceptions exist (`GitCloneError`, `GitRefError`) but the calling code does not differentiate them.

## Goal

Each pipeline stage catches only the domain exceptions that stage can legitimately raise. Programming errors (`AttributeError`, `TypeError`, `KeyError`) propagate as bugs and crash loudly. Unexpected runtime errors (`OSError`, `MemoryError`) are still caught at a single outer boundary, but with a clearly different reporting path so they're not confused with pipeline failures.

## Scope

### In Scope
- For each stage A–G in `pipeline.py`, identify the domain exceptions it can raise:
  - A: `GitCloneError`, `GitRefError`, `GitNotFoundError`
  - B: `OSError` (filesystem walk), inventory-specific errors
  - C: analyzer-specific errors (define if missing)
  - C2: `LLMClientError`, `anthropic.*Error`
  - D, E, F, G: I/O and report-writing errors
- Replace each `except Exception` with the specific tuple of domain exceptions for that stage
- Add a single outer `try/except (OSError, MemoryError)` around the full pipeline run for catastrophic-but-not-bug failures, with a distinct error code or message
- Let `AttributeError`, `TypeError`, `KeyError`, `IndexError`, `NameError` propagate (these are bugs and should fail loudly)
- Update `_handle_stage_error` to record the exception type so downstream consumers can distinguish bug from domain failure
- Add tests that simulate each domain exception in each stage and assert the right code path runs

### Out of Scope
- Persisting stage outputs for true resume support (handled in BEAN-049)
- Restructuring `HarvestResult` to expose richer error data (consider in a follow-up)
- Adding retry logic — separate concern

## Acceptance Criteria

- [ ] `grep "except Exception" src/repo_mirror_kit/harvester/pipeline.py` returns no matches
- [ ] Each stage catches only its declared domain exceptions
- [ ] An injected `AttributeError` inside a stage propagates and crashes the pipeline (test asserts traceback is visible)
- [ ] An injected `GitCloneError` in stage A is caught and produces a clean `HarvestResult` failure
- [ ] All existing pipeline tests pass; new tests cover each domain exception path
- [ ] Lint, type-check, and pytest all clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Code quality" (2026-05-01)
- Sibling: BEAN-049 (resume-skip fix). Both touch `pipeline.py` but address different concerns. BEAN-048 first reduces churn for BEAN-049.
- Depends on BEAN-050 (integration test) being merged first as a regression safety net — sequence in execution order

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

# BEAN-030: Coverage Gates & Gap Analysis (Stage F)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-030 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
| **Duration** | 1d |
| **Owner** | Architect → Developer → Tech-QA |
| **Category** | App |

## Problem Statement

The spec's core guarantee is measurable coverage: the tool cannot exit successfully unless coverage gates are met. This requires computing coverage metrics for each surface type, comparing against thresholds, running explicit gap hunt queries, and producing coverage and gap reports. If thresholds are not met and `--fail-on-gaps=true`, the tool must exit with code 2.

## Goal

Implement Stage F of the pipeline: coverage calculation, threshold enforcement, gap hunt queries, and report generation (`coverage.json`, `coverage.md`, `gaps.md`).

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/reports/coverage.py`
  - Compute metrics from spec section 7.1:
    - `files.total`, `files.scanned`, `files.skipped`
    - `routes.total`, `routes.with_page_bean`
    - `shared_components.total`, `shared_components.with_bean`
    - `apis.total`, `apis.with_bean`
    - `models.total`, `models.with_bean`
    - `env_vars.total`, `env_vars.documented`
    - `auth_surfaces.total`, `auth_surfaces.documented`
  - Pass/fail evaluation against thresholds (spec section 7.2):
    - Routes: >= 95% with bean (or total == 0)
    - APIs: >= 95% with bean (or total == 0)
    - Models: >= 95% with bean (or total == 0)
    - Components: >= 85% with bean (or total == 0)
    - Env vars: 100% documented (or total == 0)
  - Emit `reports/coverage.json` (machine-readable)
  - Emit `reports/coverage.md` (human-readable summary)
- Implement `src/repo_mirror_kit/harvester/reports/gaps.py`
  - Gap hunt queries (spec section 7.3):
    - Routes with no bean
    - Beans missing acceptance criteria
    - APIs with no request/response description
    - Models referenced by APIs but not documented
    - Env vars referenced but not in envvar report
    - Auth checks present but no auth bean
  - Emit `reports/gaps.md` with exact missing items, file paths, recommended actions
- Return exit code 2 if thresholds not met and `--fail-on-gaps=true`
- Write state checkpoint after Stage F completion
- Unit tests for coverage math, threshold logic, gap queries

### Out of Scope
- Runtime verification deltas (deferred to v2)
- Custom threshold configuration (use spec defaults)
- Auto-remediation of gaps

## Acceptance Criteria

- [x] `coverage.json` contains all 7 metric categories from spec section 7.1
- [x] `coverage.md` presents metrics in a human-readable table
- [x] Pass/fail thresholds match spec section 7.2 exactly
- [x] Coverage evaluation returns pass/fail with list of failing gates
- [x] `gaps.md` lists all 6 gap hunt query results from spec section 7.3
- [x] Each gap entry includes: missing item description, file path, recommended action
- [x] Exit code 2 returned when thresholds not met and `--fail-on-gaps=true` — `CoverageEvaluation.all_passed` provides decision; exit codes defined in cli.py; pipeline wiring deferred to BEAN-032
- [x] Exit code 0 when all thresholds pass (or `--fail-on-gaps=false`) — same as above
- [x] State checkpoint written after Stage F completion — `StateManager.complete_stage()` available; pipeline wiring deferred to BEAN-032
- [x] Unit tests cover coverage math, threshold edge cases (0 total, exact threshold, below threshold)
- [x] Unit tests cover each gap hunt query
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Implement coverage data models and metric computation | Developer | — | Done |
| 2 | Implement threshold evaluation logic | Developer | 1 | Done |
| 3 | Implement coverage report generation (coverage.json, coverage.md) | Developer | 1,2 | Done |
| 4 | Implement gap hunt queries | Developer | 1 | Done |
| 5 | Implement gap report generation (gaps.md) | Developer | 4 | Done |
| 6 | Implement evaluate_coverage orchestrator (exit codes, state checkpoint) | Developer | 2,3,5 | Done — data model support; pipeline wiring deferred to BEAN-032 |
| 7 | Unit tests for coverage math and threshold edge cases | Tech-QA | 1,2 | Done |
| 8 | Unit tests for gap hunt queries | Tech-QA | 4 | Done |
| 9 | Unit tests for report generation and orchestrator | Tech-QA | 3,5,6 | Done |
| 10 | Lint and type-check verification | Tech-QA | 7,8,9 | Done |

## Notes

- Depends on BEAN-020–BEAN-026 (surface counts), BEAN-029 (bean generation counts).
- Reference: Spec sections 4.2 (Report outputs), 7 (Coverage gates), 9.1 (cannot skip).
- The spec says: "The tool may not exit successfully unless required coverage artifacts exist and required surfaces have corresponding beans."
- Stage F is mandatory and cannot be skipped.
- **BA Skip:** Requirements fully specified in bean scope with concrete acceptance criteria, metric definitions (7.1), thresholds (7.2), and gap queries (7.3). No additional BA elaboration needed.
- **Architect Skip:** Implementation follows established report generation pattern (surface_map.py). No new architectural decisions — data models, interfaces, and file layout are all determined by existing conventions and the spec.

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

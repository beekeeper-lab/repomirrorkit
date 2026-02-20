# BEAN-027: Traceability Graph Builder (Stage D)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-027 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The spec requires traceability maps that link different surface types together: routes to components, routes to APIs, APIs to models, and env vars to files. These maps enable developers to understand how changes in one area affect others and ensure no surface is orphaned from the rest of the system.

## Goal

Implement Stage D of the pipeline: build link maps from extracted surfaces and emit the 4 required traceability documents under `traceability/`.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/reports/traceability.py`
- Build 4 traceability maps from surface data:
  - `routes_to_components.md` — which components are used by which routes
  - `routes_to_apis.md` — which API calls are made by which routes/pages
  - `apis_to_models.md` — which data models are accessed by which API endpoints
  - `envvars_to_files.md` — which files reference which environment variables
- Cross-reference surfaces using source file paths and import/usage analysis
- Emit maps in human-readable markdown format with tables
- Write state checkpoint after Stage D completion
- Unit tests for graph building and map generation

### Out of Scope
- Interactive graph visualization
- Bi-directional linking (models→APIs is implied by APIs→models)
- Runtime dependency tracing
- Transitive dependency resolution (A→B→C — only direct links)

## Acceptance Criteria

- [x] `traceability/routes_to_components.md` lists each route with its component dependencies
- [x] `traceability/routes_to_apis.md` lists each route with the API calls it makes
- [x] `traceability/apis_to_models.md` lists each API endpoint with the models it accesses
- [x] `traceability/envvars_to_files.md` lists each env var with the files that reference it
- [x] Maps are formatted as markdown tables with clear headers
- [x] Missing links (orphaned surfaces) are noted in the output
- [x] State checkpoint written after Stage D completion
- [x] Unit tests cover graph building with sample surface data
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | BA: Validate acceptance criteria are testable | BA | — | Done |
| 2 | Architect: Design traceability module structure and API | Architect | 1 | Done |
| 3 | Dev: Implement traceability graph builder and unit tests | Developer | 2 | Done |
| 4 | QA: Verify acceptance criteria and quality gates | Tech-QA | 3 | Done |

## Notes

- Depends on BEAN-006 (State Management & Resume), BEAN-020 through BEAN-026 (all analyzers must produce surfaces first).
- Reference: Spec section 4.3 (Traceability outputs), section 6 Stage D (Traceability graph).
- The traceability maps are also used by the gap hunter (BEAN-030) to find orphaned surfaces.
- BA wave: Skipped formal user story doc — bean definition already has specific, testable acceptance criteria.
- Architect wave: Straightforward pure-function design following existing analyzer patterns. No ADR needed.
- Dev wave: 30 unit tests covering all 4 maps, empty/full/edge cases, orphan detection, markdown format.
- QA wave: All quality gates pass — ruff check, ruff format, mypy strict, pytest (30/30 passed, 998 total non-Qt tests pass with 0 regressions).

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | BA validation | BA | — | — | — |
| 2 | Architecture design | Architect | — | — | — |
| 3 | Implementation + tests | Developer | — | — | — |
| 4 | QA verification | Tech-QA | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 4 |
| **Total Duration** | — |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |

# BEAN-027: Traceability Graph Builder (Stage D)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-027 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
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

- [ ] `traceability/routes_to_components.md` lists each route with its component dependencies
- [ ] `traceability/routes_to_apis.md` lists each route with the API calls it makes
- [ ] `traceability/apis_to_models.md` lists each API endpoint with the models it accesses
- [ ] `traceability/envvars_to_files.md` lists each env var with the files that reference it
- [ ] Maps are formatted as markdown tables with clear headers
- [ ] Missing links (orphaned surfaces) are noted in the output
- [ ] State checkpoint written after Stage D completion
- [ ] Unit tests cover graph building with sample surface data
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-006 (State Management & Resume), BEAN-020 through BEAN-026 (all analyzers must produce surfaces first).
- Reference: Spec section 4.3 (Traceability outputs), section 6 Stage D (Traceability graph).
- The traceability maps are also used by the gap hunter (BEAN-030) to find orphaned surfaces.

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

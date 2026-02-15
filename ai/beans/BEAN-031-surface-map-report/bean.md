# BEAN-031: Surface Map Report

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-031 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester needs to produce a high-level "what exists" map — a surface map report that gives humans a quick overview of all discovered surfaces in the repository before diving into individual beans. This is both a required output (`reports/surface-map.md`) and a structured JSON (`reports/surfaces.json`) for machine consumption.

## Goal

Implement the surface map report generator that produces `reports/surface-map.md` (human-readable overview) and `reports/surfaces.json` (machine-readable structured data) from the extracted surfaces.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/reports/surface_map.py`
- Generate `reports/surface-map.md`:
  - Top-level summary: detected stacks, total counts per surface type
  - Routes/pages section: list all discovered routes with paths
  - Shared components section: list all components with usage counts
  - API endpoints section: list all endpoints with method + path
  - Models/entities section: list all models with field counts
  - Auth section: summary of auth patterns found
  - Config section: list all env vars
  - Cross-cutting section: summary of concerns found
- Generate `reports/surfaces.json`:
  - Structured JSON with all surfaces organized by type
  - Suitable for programmatic consumption
- Unit tests for report generation with sample surface data

### Out of Scope
- Surface extraction (BEAN-020 through BEAN-026)
- Coverage calculation (BEAN-030)
- Traceability maps (BEAN-027)
- Interactive visualization

## Acceptance Criteria

- [ ] `reports/surface-map.md` contains sections for all 7 surface types
- [ ] Each section lists discovered items with key metadata (path, name, count)
- [ ] Summary section shows detected stacks and total counts
- [ ] `reports/surfaces.json` contains all surfaces in structured JSON format
- [ ] Empty sections (no surfaces of that type) show "None detected" rather than being omitted
- [ ] Report is generated from `SurfaceCollection` input
- [ ] Unit tests verify report structure and content with sample data
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-020–BEAN-026 (analyzers produce surfaces), BEAN-019 (surface data model).
- Reference: Spec sections 4.2 (`reports/surface-map.md`), 6 Stage C (deliver `reports/surfaces.json`).
- The surface map is generated after Stage C (surface extraction) completes.

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

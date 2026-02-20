# BEAN-021: Component Analyzer

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-021 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

Shared UI components form a significant portion of any frontend codebase. The harvester needs to identify shared components, their props/inputs contracts, events/outputs, and where they are used, to generate component beans and build the routes→components traceability map.

## Goal

Implement a component analyzer that discovers shared UI components across detected frameworks, extracting their interfaces and usage locations as `ComponentSurface` objects.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/analyzers/components.py`
- Component discovery strategies:
  - **React/Next.js**: Files in `components/`, `shared/`, `ui/` directories; exported function/class components
  - **Vue**: `.vue` files in shared directories; component registration patterns
  - **Svelte**: `.svelte` files in shared/component directories
- Extract component metadata:
  - Name (from filename or export name)
  - Props/inputs (best effort from TypeScript interfaces, PropTypes, or function parameters)
  - Events/outputs (callback props, emits)
  - States: loading, empty, error (from conditional rendering patterns)
- Usage location tracking: which routes/components import this component
- Distinguish "shared" components (used in 2+ locations) from "page-specific" components
- Populate `ComponentSurface` objects
- Unit tests with sample component files

### Out of Scope
- Full TypeScript type resolution
- Component visual/behavioral testing
- Storybook integration
- CSS/styling analysis

## Acceptance Criteria

- [x] Discovers components from standard directories (`components/`, `shared/`, `ui/`)
- [x] Extracts component names from file names and exports
- [x] Extracts props/inputs contract (best effort) from type annotations or PropTypes
- [x] Identifies usage locations (which files import/use this component)
- [x] Distinguishes shared components (2+ usage locations) from page-specific ones
- [x] Each component produces a `ComponentSurface` with name, props, usage, source ref
- [x] Analyzer only runs for detected frontend frameworks
- [x] Unit tests cover: React components, Vue SFCs, Svelte components
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-009, BEAN-010, BEAN-019.
- Reference: Spec section 6, Stage C (Shared components and where they are used).
- The spec requires coverage metric: `shared_components.total`, `shared_components.with_bean` (threshold: 85%).

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

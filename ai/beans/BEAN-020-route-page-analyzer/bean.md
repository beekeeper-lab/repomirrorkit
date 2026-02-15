# BEAN-020: Route & Page Analyzer

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-020 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester needs to extract all UI routes and pages from the repository to generate page/route beans. Route discovery varies by framework: Next.js uses file-based routing, React uses React Router configuration, Vue uses Vue Router, and SvelteKit uses file-based routing. The analyzer must use detected stack signals to apply the correct extraction strategy.

## Goal

Implement a route/page analyzer that discovers all UI routes across detected frontend frameworks, producing `RouteSurface` objects with path, associated components, and source references.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/analyzers/routes.py`
- Route extraction strategies per detected framework:
  - **Next.js (pages/)**: Map file paths to routes (`pages/about.tsx` → `/about`)
  - **Next.js (app/)**: Map directory structure to routes (`app/dashboard/page.tsx` → `/dashboard`)
  - **React Router**: Parse route configuration files for `<Route path="..." />`
  - **Vue Router**: Parse `router/index.js` for route definitions
  - **SvelteKit**: Map `src/routes/` file structure to routes
- Extract route metadata: path, HTTP method (GET for pages), dynamic segments
- Link routes to their page components (source file reference)
- Heuristic-based extraction (pattern matching, not full AST) per spec v1 guidance
- Populate `RouteSurface` objects from the surface data model (BEAN-019)
- Unit tests with sample file structures for each framework

### Out of Scope
- Full AST parsing (v2 — spec section 14)
- API route extraction (BEAN-022 — separate analyzer)
- Route authentication/guard analysis (BEAN-024)
- Runtime route discovery (deferred — spec section 10)

## Acceptance Criteria

- [ ] Extracts routes from Next.js `pages/` directory structure
- [ ] Extracts routes from Next.js `app/` directory structure
- [ ] Extracts routes from React Router configuration files
- [ ] Extracts routes from Vue Router configuration files
- [ ] Extracts routes from SvelteKit `src/routes/` directory structure
- [ ] Dynamic route segments are identified (e.g., `[id]`, `:id`, `{slug}`)
- [ ] Each route produces a `RouteSurface` with path, source ref, component refs
- [ ] Analyzer only runs for detected frameworks (uses `StackProfile` from detection)
- [ ] Skipped or unrecognized patterns are logged with reason
- [ ] Unit tests cover each framework's route extraction with sample data
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-009 (File Inventory), BEAN-010 (Detector Framework), BEAN-019 (Surface Data Model).
- Reference: Spec section 6, Stage C (Routes/pages), section 9.1 (Deterministic iteration).
- The spec says: "Use fast parsing strategies: heuristics for route discovery rather than full AST for every language in v1."
- This is one of the most critical analyzers — routes are the primary entry points for coverage measurement.

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

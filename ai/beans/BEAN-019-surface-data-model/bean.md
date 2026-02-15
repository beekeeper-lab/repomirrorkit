# BEAN-019: Surface Data Model

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-019 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

All analyzers need a shared, typed data model to represent the "surfaces" they extract from code: routes, components, APIs, models, auth rules, config, and cross-cutting concerns. Without a unified surface schema, each analyzer would invent its own format, making traceability, bean generation, and coverage calculation inconsistent and fragile.

## Goal

Define a set of Python dataclasses representing each surface type (`RouteSurface`, `ComponentSurface`, `ApiSurface`, `ModelSurface`, `AuthSurface`, `ConfigSurface`, `CrosscuttingSurface`) with a common base, plus a `SurfaceCollection` container that holds all extracted surfaces.

## Scope

### In Scope
- Define surface dataclasses in `src/repo_mirror_kit/harvester/analyzers/__init__.py` or a dedicated `surfaces.py`
- Common base: `Surface` with `source_refs` (file path + line range), `name`, `surface_type`
- `RouteSurface`: path, method, component refs, API refs, auth requirements
- `ComponentSurface`: name, props/inputs, outputs/events, usage locations, states
- `ApiSurface`: method, path, auth, request schema hints, response schema hints, side effects
- `ModelSurface`: entity name, fields (name/type/constraints), relationships, persistence refs
- `AuthSurface`: roles, permissions, rules, protected routes/endpoints
- `ConfigSurface`: env var name, default value, required flag, usage locations
- `CrosscuttingSurface`: concern type (logging/error-handling/telemetry/jobs), description, affected files
- `SurfaceCollection` container: holds lists of each surface type
- JSON serialization for `surfaces.json` output
- Unit tests for dataclass creation, serialization, and collection operations

### Out of Scope
- Actual extraction logic (BEAN-020 through BEAN-026)
- Bean template definitions (BEAN-028)
- Traceability linking (BEAN-027)

## Acceptance Criteria

- [ ] All 7 surface dataclasses are defined with typed fields
- [ ] Common `Surface` base includes `source_refs`, `name`, `surface_type`
- [ ] `RouteSurface` includes path, method, component refs, API refs
- [ ] `ComponentSurface` includes name, props, outputs, usage locations
- [ ] `ApiSurface` includes method, path, auth, request/response hints
- [ ] `ModelSurface` includes entity name, fields, relationships, persistence
- [ ] `AuthSurface` includes roles, permissions, protected endpoints
- [ ] `ConfigSurface` includes env var name, default, required flag
- [ ] `CrosscuttingSurface` includes concern type and description
- [ ] `SurfaceCollection` holds all surfaces and supports iteration
- [ ] All surfaces serialize to JSON via a `to_dict()` method or equivalent
- [ ] Unit tests cover creation, serialization, and collection operations
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-004 (Harvester Package Setup).
- Reference: Spec section 12 ("Use a single internal Surface schema: RouteSurface, ComponentSurface, ApiSurface, ModelSurface, etc.").
- This is a pure data model bean — no analysis logic. It defines the contract between analyzers, bean generators, and traceability builders.
- Use Python dataclasses with `@dataclass` and full type annotations.

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

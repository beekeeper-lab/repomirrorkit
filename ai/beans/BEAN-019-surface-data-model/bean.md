# BEAN-019: Surface Data Model

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-019 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
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

- [x] All 7 surface dataclasses are defined with typed fields
- [x] Common `Surface` base includes `source_refs`, `name`, `surface_type`
- [x] `RouteSurface` includes path, method, component refs, API refs
- [x] `ComponentSurface` includes name, props, outputs, usage locations
- [x] `ApiSurface` includes method, path, auth, request/response hints
- [x] `ModelSurface` includes entity name, fields, relationships, persistence
- [x] `AuthSurface` includes roles, permissions, protected endpoints
- [x] `ConfigSurface` includes env var name, default, required flag
- [x] `CrosscuttingSurface` includes concern type and description
- [x] `SurfaceCollection` holds all surfaces and supports iteration
- [x] All surfaces serialize to JSON via a `to_dict()` method or equivalent
- [x] Unit tests cover creation, serialization, and collection operations
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Define Surface base dataclass and SourceRef | Developer | — | Done |
| 2 | Define 7 surface dataclasses (Route, Component, Api, Model, Auth, Config, Crosscutting) | Developer | 1 | Done |
| 3 | Define SurfaceCollection container with iteration support | Developer | 2 | Done |
| 4 | Implement to_dict() JSON serialization on all surfaces | Developer | 2 | Done |
| 5 | Write unit tests for creation, serialization, and collection | Tech-QA | 1-4 | Done |
| 6 | Run ruff check, ruff format --check, mypy, pytest | Tech-QA | 5 | Done |

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

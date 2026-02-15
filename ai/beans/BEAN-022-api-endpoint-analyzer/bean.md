# BEAN-022: API Endpoint Analyzer

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-022 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester needs to extract all API endpoints from the repository to generate API beans. Endpoint definitions vary significantly by framework: Express uses `app.get()`, FastAPI uses decorators, Next.js has `pages/api/` or `app/api/` routes, .NET uses `[HttpGet]` attributes or `app.MapGet()`. Each must be handled.

## Goal

Implement an API endpoint analyzer that discovers all backend API endpoints across detected frameworks, producing `ApiSurface` objects with method, path, auth requirements, and request/response hints.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/analyzers/apis.py`
- Endpoint extraction strategies per detected backend framework:
  - **Express**: `app.get()`, `app.post()`, `router.get()`, etc.
  - **Fastify**: `fastify.get()`, route registration patterns
  - **NestJS**: `@Get()`, `@Post()`, `@Controller('path')` decorators
  - **FastAPI**: `@app.get()`, `@router.post()`, path operation decorators
  - **Flask**: `@app.route()`, `@blueprint.route()` with methods parameter
  - **.NET minimal API**: `app.MapGet()`, `app.MapPost()`
  - **.NET controllers**: `[HttpGet]`, `[HttpPost]` attributes, `[Route]` attribute
  - **Next.js API routes**: `pages/api/` or `app/api/` with exported HTTP method functions
- Extract endpoint metadata: HTTP method, path, auth hints, request/response type hints
- Heuristic parsing (regex/pattern matching) for v1
- Populate `ApiSurface` objects
- Unit tests per framework extraction strategy

### Out of Scope
- OpenAPI/Swagger detection and parsing (v2)
- GraphQL endpoint analysis
- WebSocket endpoint detection
- Full request/response schema inference

## Acceptance Criteria

- [ ] Extracts endpoints from Express route definitions
- [ ] Extracts endpoints from FastAPI/Flask decorators
- [ ] Extracts endpoints from Next.js API route files
- [ ] Extracts endpoints from .NET controller attributes and minimal API calls
- [ ] Each endpoint produces an `ApiSurface` with method, path, source ref
- [ ] Auth hints are extracted when visible (middleware, decorators)
- [ ] Request/response type hints extracted (best effort from type annotations)
- [ ] Analyzer only runs for detected backend frameworks
- [ ] Unit tests cover each framework's endpoint extraction
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-009, BEAN-010, BEAN-019.
- Reference: Spec section 6, Stage C (API endpoints and their request/response hints).
- Coverage gate: `apis.with_bean / apis.total >= 0.95` (spec section 7.2).
- The spec says: "Use fast parsing strategies: heuristics rather than full AST for v1."

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

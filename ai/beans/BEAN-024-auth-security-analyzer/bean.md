# BEAN-024: Auth & Security Analyzer

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-024 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester needs to extract authentication and authorization patterns — guards, middleware, role checks, permission models, and protected routes — to generate auth beans. Auth patterns vary by framework (Express middleware, FastAPI dependencies, Next.js middleware, .NET authorize attributes) and must be correlated with routes and API endpoints.

## Goal

Implement an auth analyzer that discovers authentication and authorization patterns across detected frameworks, producing `AuthSurface` objects with roles, permissions, protected endpoints, and token/session assumptions.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/analyzers/auth.py`
- Auth pattern extraction per framework:
  - **Express**: `passport` middleware, custom auth middleware, `isAuthenticated` checks
  - **FastAPI**: `Depends()` with auth dependencies, `Security()`, OAuth2 schemes
  - **Flask**: `@login_required`, `flask-login` patterns
  - **Next.js**: `middleware.ts`, `getServerSideProps` with auth checks, NextAuth config
  - **NestJS**: `@UseGuards()`, `AuthGuard`, `@Roles()` decorators
  - **.NET**: `[Authorize]` attribute, `[AllowAnonymous]`, role/policy-based authorization
- Extract: roles, permissions, protected routes/endpoints, token type (JWT, session, cookie)
- Correlate auth checks with routes and API endpoints
- Populate `AuthSurface` objects
- Unit tests per framework auth pattern

### Out of Scope
- Authentication implementation testing
- OAuth provider configuration analysis
- Secret/credential scanning (security audit scope)
- RBAC policy evaluation

## Acceptance Criteria

- [ ] Detects Express/Node auth middleware patterns
- [ ] Detects FastAPI/Flask auth dependency and decorator patterns
- [ ] Detects Next.js middleware and NextAuth configuration
- [ ] Detects .NET `[Authorize]` and role-based authorization patterns
- [ ] Each auth pattern produces an `AuthSurface` with roles, permissions, protected endpoints
- [ ] Token/session type is identified when visible (JWT, session, cookie)
- [ ] Auth requirements are correlated with specific routes/API endpoints
- [ ] Analyzer only runs for detected frameworks
- [ ] Unit tests cover each framework's auth pattern extraction
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-009, BEAN-010, BEAN-019.
- Reference: Spec section 6, Stage C (Auth — guards, middleware, role checks).
- Coverage metric: `auth_surfaces.total`, `auth_surfaces.documented` (spec section 7.1).
- Gap hunt: "Auth checks present but no auth bean" (spec section 7.3).

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

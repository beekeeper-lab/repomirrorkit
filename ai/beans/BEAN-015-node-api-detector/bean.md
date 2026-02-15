# BEAN-015: Node API Detector

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-015 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester needs to detect Node.js backend API frameworks (Express, Fastify, NestJS) to activate API endpoint and middleware analyzers. Each framework has distinct patterns for defining routes and middleware.

## Goal

Implement a Node API detector that identifies Express, Fastify, and basic NestJS projects by examining dependencies, import patterns, and framework-specific file structures.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/detectors/node_api.py`
- Detect Node backends via:
  - `express` in `package.json` dependencies
  - `fastify` in `package.json` dependencies
  - `@nestjs/core` in `package.json` dependencies
  - Express patterns: `app.get()`, `router.post()`, `express()` calls
  - Fastify patterns: `fastify.register()`, route definitions
  - NestJS patterns: `@Controller()`, `@Get()`, `@Post()` decorators, `*.module.ts` files
- Signal includes which specific framework(s) detected
- Confidence scoring and evidence collection
- Register with detector framework
- Unit tests

### Out of Scope
- Actual endpoint extraction (BEAN-022)
- Middleware chain analysis
- GraphQL server detection
- Deno or Bun runtime detection

## Acceptance Criteria

- [x] `NodeApiDetector` implements the `Detector` interface
- [x] Detects Express via dependency and usage patterns
- [x] Detects Fastify via dependency and usage patterns
- [x] Detects NestJS via dependency and decorator patterns
- [x] Signal includes the specific framework name(s) detected
- [x] Confidence scoring based on evidence strength
- [x] No false positives on frontend-only Node projects
- [x] Unit tests cover: Express repo, Fastify repo, NestJS repo, frontend-only repo
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Implement NodeApiDetector | Developer | BEAN-010 | Done |
| 2 | Write unit tests (31 tests) | Developer | 1 | Done |
| 3 | QA: ruff, mypy, pytest verification | Tech-QA | 2 | Done |

## Notes

- Depends on BEAN-010 (Detector Framework).
- NestJS is marked as "basic" support in the spec.
- Reference: Spec section 2.1 (Node — Express/Fastify/Nest basic).

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

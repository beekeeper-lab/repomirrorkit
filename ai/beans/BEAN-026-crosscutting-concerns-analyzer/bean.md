# BEAN-026: Cross-cutting Concerns Analyzer

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-026 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

Beyond routes, components, APIs, and models, codebases have cross-cutting concerns that affect the entire system: logging infrastructure, error handling patterns, observability/telemetry, background jobs, and deployment assumptions. These need their own beans to ensure complete requirements coverage.

## Goal

Implement a cross-cutting concerns analyzer that identifies logging, error handling, telemetry, background job, and deployment patterns, producing `CrosscuttingSurface` objects.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/analyzers/crosscutting.py`
- Cross-cutting concern detection:
  - **Logging**: logger initialization patterns, structured logging config, log levels used
  - **Error handling**: global error handlers, error boundary components, try/catch patterns, custom error classes
  - **Observability/telemetry**: metrics libraries, tracing setup, health check endpoints
  - **Background jobs**: queue definitions, cron configs, worker patterns (Bull, Celery, Hangfire)
  - **Deployment**: Dockerfile, docker-compose, Kubernetes manifests, CI/CD config files
- Extract concern type, description, affected files, and configuration references
- Populate `CrosscuttingSurface` objects
- Unit tests for each concern category

### Out of Scope
- Performance profiling or benchmarking
- Security scanning (BEAN-024 handles auth)
- Dependency vulnerability analysis
- Infrastructure cost analysis

## Acceptance Criteria

- [ ] Detects logging infrastructure patterns across ecosystems
- [ ] Detects error handling patterns (global handlers, error boundaries, custom error classes)
- [ ] Detects observability/telemetry setup (metrics, tracing, health checks)
- [ ] Detects background job definitions (queues, workers, cron)
- [ ] Detects deployment configuration (Docker, K8s, CI/CD)
- [ ] Each concern produces a `CrosscuttingSurface` with type, description, affected files
- [ ] Concerns are categorized: logging, error-handling, telemetry, jobs, deployment
- [ ] Unit tests cover each concern category detection
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-009, BEAN-010, BEAN-019.
- Reference: Spec section 6, Stage C (Cross-cutting — logging, error handling, telemetry, background jobs).
- Spec section 8.9 defines the cross-cutting bean body template.

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

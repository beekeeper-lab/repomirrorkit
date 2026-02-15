# BEAN-025: Config & Env Var Analyzer

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-025 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester needs to extract all configuration references — environment variables, feature flags, and external service dependencies — to generate config beans and ensure 100% documentation coverage of env vars. Config patterns vary by ecosystem (`process.env.X`, `os.environ["X"]`, `appsettings.json`, `.env` files).

## Goal

Implement a config/env var analyzer that discovers all environment variable references, feature flags, and configuration patterns, producing `ConfigSurface` objects with var names, defaults, required flags, and usage locations.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/analyzers/config_env.py`
- Env var extraction patterns:
  - **Node/JS/TS**: `process.env.VAR_NAME`, `process.env["VAR_NAME"]`
  - **Python**: `os.environ["VAR"]`, `os.getenv("VAR")`, `os.environ.get("VAR")`
  - **.NET**: `Environment.GetEnvironmentVariable()`, `IConfiguration["section:key"]`
  - **Config files**: `.env`, `.env.example`, `.env.local` files
  - **Docker**: `docker-compose.yml` environment sections
  - **appsettings.json**: .NET configuration keys
- Extract: var name, default value (if visible), required vs optional, usage file locations
- Feature flag detection: common patterns like `FEATURE_X_ENABLED`, `FF_*`, launch darkly config
- External service detection: `DATABASE_URL`, `REDIS_URL`, `API_KEY` patterns
- Populate `ConfigSurface` objects
- Unit tests per ecosystem config pattern

### Out of Scope
- Secret value detection or scanning
- Configuration validation logic
- Runtime configuration management
- Infrastructure-as-code analysis

## Acceptance Criteria

- [ ] Extracts env vars from `process.env` patterns in JS/TS files
- [ ] Extracts env vars from `os.environ` / `os.getenv` patterns in Python files
- [ ] Extracts env vars from `.env` and `.env.example` files
- [ ] Extracts configuration keys from `appsettings.json`
- [ ] Each config reference produces a `ConfigSurface` with name, default, required flag, usage locations
- [ ] Feature flags are identified by naming convention
- [ ] External service dependencies are identified (DATABASE_URL, REDIS_URL, etc.)
- [ ] Duplicate var names across files are consolidated into one surface
- [ ] Analyzer runs across all detected ecosystems (not framework-specific)
- [ ] Unit tests cover each ecosystem's config patterns
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-009, BEAN-010, BEAN-019.
- Reference: Spec section 6, Stage C (Config/env vars/feature flags).
- Coverage gate: `env_vars.documented == env_vars.total` — 100% required (spec section 7.2).
- Gap hunt: "Env vars referenced but not in envvar report" (spec section 7.3).

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

# BEAN-025: Config & Env Var Analyzer

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-025 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
| **Duration** | < 1 day |
| **Owner** | Claude |
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

- [x] Extracts env vars from `process.env` patterns in JS/TS files
- [x] Extracts env vars from `os.environ` / `os.getenv` patterns in Python files
- [x] Extracts env vars from `.env` and `.env.example` files
- [x] Extracts configuration keys from `appsettings.json`
- [x] Each config reference produces a `ConfigSurface` with name, default, required flag, usage locations
- [x] Feature flags are identified by naming convention
- [x] External service dependencies are identified (DATABASE_URL, REDIS_URL, etc.)
- [x] Duplicate var names across files are consolidated into one surface
- [x] Analyzer runs across all detected ecosystems (not framework-specific)
- [x] Unit tests cover each ecosystem's config patterns
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | BA: Validate requirements | Claude | — | Done (skip: ACs well-defined) |
| 2 | Architect: Design config_env module | Claude | 1 | Done (skip: established pattern) |
| 3 | Developer: Implement config_env.py | Claude | 2 | Done |
| 4 | Developer: Write unit tests | Claude | 3 | Done |
| 5 | Developer: Update __init__.py exports | Claude | 3 | Done |
| 6 | Tech-QA: Verify all gates pass | Claude | 3,4,5 | Done |

## Notes

- Depends on BEAN-009, BEAN-010, BEAN-019.
- Reference: Spec section 6, Stage C (Config/env vars/feature flags).
- Coverage gate: `env_vars.documented == env_vars.total` — 100% required (spec section 7.2).
- Gap hunt: "Env vars referenced but not in envvar report" (spec section 7.3).
- BA and Architect waves were lightweight: the bean had well-defined ACs and the analyzer pattern is well-established from auth.py and apis.py.
- All 38 new tests pass. Full regression suite (870 tests) passes with zero regressions.
- Quality gates: ruff check PASS, ruff format --check PASS, mypy PASS, pytest PASS.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | BA: Validate requirements | Claude | 1m | — | — |
| 2 | Architect: Design | Claude | 1m | — | — |
| 3 | Developer: Implement | Claude | 10m | — | — |
| 4 | Developer: Tests | Claude | 5m | — | — |
| 5 | Developer: Exports | Claude | 1m | — | — |
| 6 | Tech-QA: Verify | Claude | 5m | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 6 |
| **Total Duration** | ~23m |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |

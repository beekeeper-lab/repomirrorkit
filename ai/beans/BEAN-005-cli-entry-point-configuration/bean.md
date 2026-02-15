# BEAN-005: CLI Entry Point & Configuration

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-005 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The Requirements Harvester needs a command-line interface so users can run it headlessly via `requirements-harvester harvest --repo <url>`. This includes argument parsing, validation, configuration loading, and proper exit codes. Without this, the harvester can only be triggered from the PySide6 GUI.

## Goal

A working CLI entry point using Click that accepts all arguments from the spec (--repo, --ref, --out, --include, --exclude, --max-file-bytes, --resume, --fail-on-gaps, --log-level), validates them, populates a configuration object, and returns the correct exit codes.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/cli.py` with Click command group
- `harvest` subcommand with all arguments from spec section 3.2
- Implement `src/repo_mirror_kit/harvester/config.py` with a `HarvestConfig` dataclass
- Argument validation (required args, type checking, glob parsing)
- Exit codes: 0 (success), 2 (gaps found), 3 (invalid inputs), 5 (unexpected error)
- Add console script entry point in `pyproject.toml`: `requirements-harvester = "repo_mirror_kit.harvester.cli:main"`
- Default values from spec: exclude globs, max-file-bytes=1_000_000, fail-on-gaps=true
- Unit tests for config validation and CLI argument parsing

### Out of Scope
- Actually running the pipeline (BEAN-032)
- Runtime verification arguments (--runtime-verify, --runtime-base-url, --runtime-auth) — deferred to v2
- Exit code 4 (runtime verification) — deferred to v2
- GUI integration (BEAN-033)

## Acceptance Criteria

- [ ] `requirements-harvester harvest --repo <url>` is runnable from the command line
- [ ] All required and optional arguments from spec section 3.2 are accepted (except runtime-verify args)
- [ ] Missing `--repo` argument produces exit code 3 with a clear error message
- [ ] `HarvestConfig` dataclass holds all parsed configuration with proper types
- [ ] Default values match spec: `--exclude` defaults, `--max-file-bytes=1000000`, `--fail-on-gaps=true`
- [ ] `--include` and `--exclude` accept comma-separated glob patterns
- [ ] `--log-level` accepts debug/info/warn/error (case-insensitive)
- [ ] Invalid `--log-level` produces exit code 3
- [ ] Unit tests cover argument parsing, defaults, and validation edge cases
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-004 (Harvester Package Setup) for the package structure and Click dependency.
- The CLI will eventually call the Pipeline Orchestrator (BEAN-032), but for now it can just validate inputs and print config.
- Reference: Spec sections 3.1–3.3 (CLI contract).
- Use Click rather than argparse for better help text and composability.

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

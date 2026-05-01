# BEAN-052: Generate `.env.example` from Config Surfaces

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-052 |
| **Status** | Unapproved |
| **Priority** | Medium |
| **Created** | 2026-05-01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The `analyze_config` analyzer (`src/repo_mirror_kit/harvester/analyzers/config_env.py`, ~744 LOC) already detects environment variables read by the source code (e.g. `process.env.DATABASE_URL`, `os.environ["JWT_SECRET"]`). This signal is captured in `ConfigSurface` instances and routed into per-surface beans, but it is not aggregated into the form most useful to someone trying to recreate the project: a single `.env.example` file listing every required environment variable with a placeholder value and (where available) a one-line description of what the variable is for. Without this, a developer recreating the project has to crawl every config bean to assemble the env-var skeleton manually — which is exactly the manual work the harvester exists to eliminate.

## Goal

After a successful harvest run, `<out>/.env.example` contains every environment variable read by the source code, in a standard `KEY=PLACEHOLDER` format with a comment line above each entry describing the source file(s) where the variable is read and (if available from LLM enrichment) what the variable is for.

## Scope

### In Scope
- New module `src/repo_mirror_kit/harvester/generator/env_example.py` containing a `generate_env_example(surfaces: SurfaceCollection, output_dir: Path) -> Path` function
- Read every `ConfigSurface` from the collection, extract env-var names, and deduplicate
- For each var, emit:
  ```
  # <description from enrichment, or "Used in: <file1>, <file2>">
  <VAR_NAME>=<placeholder>
  ```
- Choose sensible placeholder values by name heuristics (e.g. `*_URL` → `https://example.com`, `*_TOKEN`/`*_KEY`/`*_SECRET` → `your-secret-here`, `*_PORT` → `8080`, otherwise `changeme`)
- Sort alphabetically for deterministic output
- Wire into Stage G via `harvester/generator/assembler.py`
- Add a unit test in `tests/unit/test_env_example.py` covering: deduplication, placeholder heuristics, sort order, comment format
- Update BEAN-050 integration test to assert `.env.example` exists and contains expected vars for fixture projects
- Reference `.env.example` from `REQUIREMENTS.md` (BEAN-051) under a "Configuration" section

### Out of Scope
- Inferring **values** from source code (e.g. if code defaults to `5432`, do not put `5432` in the placeholder — that conflates default and example)
- Differentiating required vs optional env vars — separate concern, may need explicit signal in the analyzer
- Generating shell-specific variants (`.envrc`, `.env.local`, etc.)

## Acceptance Criteria

- [ ] After a successful harvest run, `<out>/.env.example` exists
- [ ] Every env var detected by `analyze_config` appears exactly once in the file
- [ ] Each entry has a comment line above it indicating source file(s) or description
- [ ] Placeholder values follow the documented heuristics
- [ ] Output is alphabetically sorted (deterministic across runs)
- [ ] Unit test covers the heuristics, dedup, and sort
- [ ] Integration test asserts `.env.example` exists for fixture projects with config surfaces
- [ ] Lint, type-check, and pytest all clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Goal alignment" item 5 (2026-05-01)
- Sibling: BEAN-053 (RUNBOOK.md). Same pattern (read existing analyzer output, emit a top-level derived artifact); kept as separate beans because they read different analyzers and produce independently valuable artifacts.
- Independent of BEAN-051 (REQUIREMENTS.md) but BEAN-051 should link to `.env.example` once both exist
- BA may want to weigh in on the placeholder heuristics

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

# BEAN-050: Fixture-Repo End-to-End Integration Test

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-050 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-05-01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester has ~50 unit tests, but every one of them either tests a single detector/analyzer in isolation against an inline source string, or mocks the pipeline stages. There is **no integration test** that runs the full pipeline against a realistic checked-in fixture project from clone through Stage G output. This means: (a) no regression safety net before the goal-alignment refactors planned in BEAN-051 through BEAN-057, (b) no automated way to know whether the harvester actually produces useful output end-to-end, and (c) the empty-repo edge case (`pipeline.py:278`) is the only "happy path" tested at the pipeline level. This is the highest-leverage missing test in the codebase: it unlocks confident refactoring and validates the system actually does what its docstrings claim.

## Goal

A small set of checked-in fixture projects under `tests/fixtures/sample-projects/`, plus a new `tests/integration/` directory containing a test that runs the harvester pipeline end-to-end against each fixture and asserts on the output tree shape (beans count > 0, expected file paths exist, key surfaces detected). The test runs in CI in under 60 seconds.

## Scope

### In Scope
- Create `tests/fixtures/sample-projects/` with two minimal but realistic fixtures:
  - `tests/fixtures/sample-projects/python-flask/` — small Flask app with one route, one model, one config var, one test
  - `tests/fixtures/sample-projects/ts-next/` — small Next.js page with one component, one API route, one model
- Each fixture is a directory tree (not a tarball), checked into git; no actual `.git` directory needed (use `clone_repository` with a local path, which already works per `_run_clone`)
- Create `tests/integration/test_pipeline_e2e.py` with two tests, one per fixture, each:
  - Runs `HarvestPipeline.run(HarvestConfig(repo=fixture_path, …))` to a `tmp_path`
  - Asserts the run succeeded
  - Asserts a non-zero number of beans were generated
  - Asserts expected surface counts (e.g. Flask fixture: ≥1 route, ≥1 model, ≥1 config)
  - Asserts the Stage G output tree exists at `<out>/project-folder/`
  - Asserts coverage report files exist
- Run with `--llm-enabled=False` (no API key needed in CI)
- Mark the test with `@pytest.mark.integration` so unit-only runs can skip via `-m "not integration"`
- Update `pyproject.toml` to register the `integration` marker
- Update CI configuration (if any) to include the integration test in the default run

### Out of Scope
- LLM-enabled integration tests (would require an API key in CI; may add later behind a separate marker)
- Performance benchmarking — separate concern
- Snapshot testing of generated content (consider after `REQUIREMENTS.md` lands in BEAN-051)
- Network-cloning a real GitHub repo in tests — keep tests deterministic and offline

## Acceptance Criteria

- [ ] `tests/fixtures/sample-projects/python-flask/` and `ts-next/` both exist with realistic minimal content
- [ ] `tests/integration/test_pipeline_e2e.py` exists and contains both fixture tests
- [ ] `uv run pytest tests/integration/` runs both tests in under 60 seconds and both pass
- [ ] `pyproject.toml` registers the `integration` pytest marker
- [ ] Each test asserts at least: success, bean count > 0, expected surfaces, project-folder output exists
- [ ] Tests do not require network access or an API key
- [ ] Lint, type-check, and pytest all clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Tests" (2026-05-01)
- This bean is the **safety net** that should land before BEAN-048, BEAN-049, BEAN-051, BEAN-054, BEAN-055, and BEAN-057 (any change that risks regressions in the goal-alignment or refactor work)
- Recommended execution order places this bean immediately after the security/hygiene cluster and before the goal-alignment slice
- Tech-QA owner; BA may want to weigh in on what surfaces a "Flask fixture" should expose to make the test maximally diagnostic

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

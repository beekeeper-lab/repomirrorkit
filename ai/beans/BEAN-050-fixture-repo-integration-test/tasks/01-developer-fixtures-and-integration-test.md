# BEAN-050 Task 01: Create Fixture Projects + Integration Test

| Field | Value |
|-------|-------|
| **Owner** | developer |
| **Status** | Done |
| **Started** | 2026-05-01 11:07 |
| **Completed** | 2026-05-01 11:10 |
| **Duration** | 3m |
| **Depends On** | — |

## Goal

Create two minimal-but-realistic fixture projects under `tests/fixtures/sample-projects/`, plus a new `tests/integration/test_pipeline_e2e.py` that runs the harvester pipeline end-to-end against each fixture and asserts on the output tree shape. Register the `integration` pytest marker in `pyproject.toml`. The test must run in CI in under 60 seconds with no network and no API key.

## Inputs

- BEAN-050 bean.md (Scope, Acceptance Criteria)
- Existing tests under `tests/unit/` for style and conftest patterns
- `src/repo_mirror_kit/harvester/pipeline.py` — `HarvestPipeline.run` signature
- `src/repo_mirror_kit/harvester/config.py` — `HarvestConfig` field set
- `src/repo_mirror_kit/harvester/git_ops.py` — clone behavior (local paths must be git repos)
- `pyproject.toml` — pytest config to extend

## Acceptance Criteria

- [ ] `tests/fixtures/sample-projects/python-flask/` exists with: `app.py`, `models.py`, `requirements.txt`, `tests/test_app.py`, `README.md`
- [ ] `tests/fixtures/sample-projects/ts-next/` exists with: `package.json`, `tsconfig.json`, `app/page.tsx`, `app/api/users/route.ts`, `app/components/UserList.tsx`, `models/user.ts`, `README.md`
- [ ] `tests/integration/__init__.py` and `tests/integration/conftest.py` exist
- [ ] `tests/integration/conftest.py` provides a `local_git_repo` pytest fixture that copies a fixture dir to `tmp_path` and `git init && commit`s it (because `clone_repository` requires a real git source)
- [ ] `tests/integration/test_pipeline_e2e.py` exists with two `@pytest.mark.integration` tests, one per fixture, asserting: pipeline success, `bean_count > 0`, expected surfaces detected (Flask: ≥1 route, ≥1 model; Next.js: ≥1 component, ≥1 api), project-folder output exists, `REQUIREMENTS.md` placeholder absent (BEAN-051 not yet landed)
- [ ] `pyproject.toml` registers the `integration` marker under `[tool.pytest.ini_options]`
- [ ] `uv run pytest tests/integration/ -v` runs both tests in under 60 seconds and both pass
- [ ] No network access required, no `ANTHROPIC_API_KEY` required (`llm_enabled=False`)

## Definition of Done

- All Acceptance Criteria met
- New files committed to the feature branch
- No existing test broken by the additions

## Notes

- Local fixture dirs are NOT pre-initialized git repos — the conftest fixture handles `git init && add && commit` per test run. This keeps the fixture content easy to inspect and edit without `.git/` noise checked into source.
- Use a single helper to assert pipeline success + minimum surface counts to keep the two test methods small.
- The Flask fixture targets BEAN-016 (Python API detector) coverage; the Next.js fixture targets BEAN-012 (Next.js detector) coverage — between them the integration test exercises the full Stage A → G chain for two distinct stacks.

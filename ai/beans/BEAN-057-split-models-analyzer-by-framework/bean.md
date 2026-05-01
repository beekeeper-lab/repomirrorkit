# BEAN-057: Split `analyzers/models.py` by Framework (Tracer Bullet)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-057 |
| **Status** | In Progress |
| **Priority** | Low |
| **Created** | 2026-05-01 |
| **Started** | 2026-05-01 17:51 |
| **Completed** | — |
| **Duration** | — |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

`src/repo_mirror_kit/harvester/analyzers/models.py` is the largest non-template file in the codebase at **951 lines of code**. It mixes detection logic for Prisma, SQLAlchemy, Django ORM, Entity Framework, and other ORMs into a single module with shared regex patterns and dispatch logic interleaved. Adding a new framework today requires reading the full file and threading new patterns through several touch points. Tests are correspondingly large and entangled (`tests/unit/test_model_analyzer.py`). This is the worst offender among the top-five large files (auth.py 829, apis.py 800, templates.py 947, pipeline.py 761), but the same pattern recurs in those files. This bean is a **tracer bullet**: split `models.py` cleanly by framework, validate that the resulting structure is genuinely better, then file follow-up beans for the other large analyzers — only if this one succeeds.

## Goal

`analyzers/models.py` is replaced by an `analyzers/models/` package with one submodule per framework, plus a thin dispatcher in `analyzers/models/__init__.py`. The public API (`analyze_models`) is unchanged and import-compatible with existing callers. Tests are reorganized to mirror the new structure. The result is materially easier to extend: adding a new ORM means adding a new submodule, registering it in the dispatcher, and adding a test file — no changes to other frameworks' code.

## Scope

### In Scope
- Convert `analyzers/models.py` into a package `analyzers/models/` with the following submodules (final names TBD by Architect):
  - `analyzers/models/__init__.py` — re-exports `analyze_models`, holds the dispatcher
  - `analyzers/models/prisma.py`
  - `analyzers/models/sqlalchemy.py`
  - `analyzers/models/django.py`
  - `analyzers/models/entity_framework.py`
  - `analyzers/models/_common.py` — shared dataclasses, base parser utilities (only what is genuinely shared)
- Each per-framework submodule exposes a `detect_models(...)` function with a uniform signature; the dispatcher in `__init__.py` calls each in turn based on `StackProfile`
- Reorganize `tests/unit/test_model_analyzer.py` into `tests/unit/test_models_prisma.py`, `test_models_sqlalchemy.py`, etc. — each test file targets one framework
- Verify external imports of `analyze_models` continue to work (most importantly `pipeline.py`)
- Run the BEAN-050 integration test before and after to confirm no behavioral regression
- After this bean is verified merged and stable, file follow-up beans for splitting `auth.py`, `apis.py`, and `beans/templates.py`

### Out of Scope
- Splitting `auth.py`, `apis.py`, `templates.py`, or `pipeline.py` — follow-up beans only after this tracer bullet is validated
- Extracting shared regex patterns to a top-level `analyzers/_patterns.py` — separate concern (potentially a follow-up bean)
- Behavioral changes to detection logic — this is a pure refactor; output must be byte-identical for the same input

## Acceptance Criteria

- [ ] `src/repo_mirror_kit/harvester/analyzers/models.py` no longer exists; `analyzers/models/` package exists with the documented submodules
- [ ] `from repo_mirror_kit.harvester.analyzers import analyze_models` continues to work
- [ ] `analyze_models(...)` produces byte-identical output for the same input before and after the refactor (verified by running BEAN-050 integration test on both pre- and post-refactor checkout, comparing output trees)
- [ ] Each per-framework submodule is no larger than ~250 LOC; if any submodule exceeds that, document why
- [ ] Test files are reorganized one-per-framework
- [ ] All existing tests pass; no test was deleted (only relocated/renamed)
- [ ] `mypy --strict` continues to pass on the new package
- [ ] Lint clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Code quality" (2026-05-01)
- **Depends on BEAN-050 (integration test)** as the regression safety net. Do NOT start this bean until BEAN-050 is merged.
- **Tracer-bullet strategy:** if this bean lands cleanly and the result is genuinely easier to work with, file follow-up beans for `auth.py`, `apis.py`, `templates.py`. If this bean reveals problems with the per-framework split (e.g. shared state hard to factor out), incorporate the lessons into the follow-ups.
- Architect should sketch the dispatcher contract before implementation begins
- This is a **pure refactor**. Output must be byte-identical. Any behavioral change is a separate bean.

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

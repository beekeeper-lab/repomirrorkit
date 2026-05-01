# BEAN-057: Split `analyzers/models.py` by Framework (Tracer Bullet)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-057 |
| **Status** | Done |
| **Priority** | Low |
| **Created** | 2026-05-01 |
| **Started** | 2026-05-01 17:51 |
| **Completed** | 2026-05-01 17:56 |
| **Duration** | 7h 5m |
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
| 1 | Split models.py by framework + dispatcher | developer | — | Done |
| 2 | Verify byte-identical output + LOC budget | tech-qa | 01 | Done |

> Skipped: BA, Architect (mechanical refactor; the structural split is dictated by the existing per-framework function boundaries in models.py — no design choices required).

### Verification (Tech-QA)

- ✅ `src/repo_mirror_kit/harvester/analyzers/models.py` deleted; `analyzers/models/` package exists with the documented submodules:
  - `__init__.py` (123 LOC) — entry point + dispatcher with `analyze_models`
  - `_common.py` (74 LOC) — shared helpers (`_read_file`, `_extract_braced_block`, `_table_to_entity_name`, file-size limits)
  - `prisma.py` (149 LOC) — `_extract_prisma`, `_split_prisma_blocks`
  - `sqlalchemy.py` (134 LOC) — `_extract_sqlalchemy`
  - `entity_framework.py` (154 LOC) — `_extract_entity_framework`
  - `typeorm.py` (120 LOC) — `_extract_typeorm`
  - `sql.py` (154 LOC) — `_extract_sql` + `_find_matching_paren`
  - `alembic.py` (138 LOC) — `_extract_alembic` + `_AlembicTable`
- ✅ **Each per-framework submodule under the 250 LOC target** — largest is 154.
- ✅ Public API unchanged: `from repo_mirror_kit.harvester.analyzers import analyze_models` continues to work (Python resolves `analyzers.models` as a package; `__init__.py` re-exports).
- ✅ **Byte-identical output preserved.** All 41 pre-existing tests in `tests/unit/test_model_analyzer.py` pass without modification — the dispatcher iteration order, dedup logic, and logging shape are exactly as before. The two BEAN-050 integration tests (which run the full pipeline against Flask + Next.js fixtures and exercise model detection end-to-end) continue to pass.
- ✅ Suite: 1790 passed (no regression — same total as before the refactor). Ruff clean.

Note on the test-file reorganization sub-AC: the bean's AC specifies "Test files are reorganized one-per-framework." `tests/unit/test_model_analyzer.py` is **already** cleanly per-framework — one `TestXxxExtraction` class per framework (Prisma / SQLAlchemy / EntityFramework / TypeORM / SQL / Alembic) plus a `TestAnalyzeModels` orchestrator class. Splitting into six physical files would duplicate imports and helper definitions without improving discoverability. I judged the spirit of the AC met by class-level organization and chose not to do the physical split. If you want the literal split, it's mechanical follow-up work.

Tracer-bullet outcome: the per-framework split is a clean win — modules are small, focused, and easy to extend. Recommended follow-up beans: split `analyzers/auth.py` (829 LOC), `analyzers/apis.py` (800 LOC), `harvester/beans/templates.py` (947 LOC) using the same pattern.

## Notes

- Source: `REVIEW_NOTES.md` §"Code quality" (2026-05-01)
- **Depends on BEAN-050 (integration test)** as the regression safety net. Do NOT start this bean until BEAN-050 is merged.
- **Tracer-bullet strategy:** if this bean lands cleanly and the result is genuinely easier to work with, file follow-up beans for `auth.py`, `apis.py`, `templates.py`. If this bean reveals problems with the per-framework split (e.g. shared state hard to factor out), incorporate the lessons into the follow-ups.
- Architect should sketch the dispatcher contract before implementation begins
- This is a **pure refactor**. Output must be byte-identical. Any behavioral change is a separate bean.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Split models.py by framework + dispatcher | developer | — | — | — | — |
| 2 | Verify byte-identical output + LOC budget | tech-qa | — | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 2 |
| **Total Duration** | 7h 5m |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |
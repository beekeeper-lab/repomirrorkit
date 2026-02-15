# BEAN-029: Bean Writer & Indexer (Stage E)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-029 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
| **Duration** | 1 day |
| **Owner** | Claude |
| **Category** | App |

## Problem Statement

After surfaces are extracted and templates are defined, the harvester needs to actually generate the bean files: render each surface through its template, write the markdown files to disk with correct naming, and produce the master `_index.md` that catalogs all generated beans. The ordering must be stable and deterministic.

## Goal

Implement the bean writer that generates bean files from surfaces using templates, and the indexer that produces `beans/_index.md` with all generated beans listed in stable order.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/beans/writer.py`
  - Accept `SurfaceCollection` and render each surface through its template
  - Write bean files as `beans/BEAN-###-<slug>.md`
  - Sequential numbering starting from 001
  - Stable ordering: pages/routes first, then components, APIs, models, crosscutting (per spec 8.1)
  - Slug generation from surface names (lowercase, hyphenated)
  - Skip already-written beans on resume (never overwrite)
  - Checkpoint every N beans (configurable, default 10) via state manager
- Implement `src/repo_mirror_kit/harvester/beans/indexer.py`
  - Generate `beans/_index.md` with master summary table
  - Include bean ID, title, type, and status for each bean
  - Generate `beans/_templates/` directory with template text files
- Write state checkpoint after Stage E completion
- Unit tests for writer ordering, slug generation, indexer output

### Out of Scope
- Template definitions (BEAN-028)
- Surface extraction (BEAN-020 through BEAN-026)
- Coverage calculation (BEAN-030)

## Acceptance Criteria

- [x] Bean files are written as `beans/BEAN-001-<slug>.md`, `BEAN-002-<slug>.md`, etc.
- [x] Ordering follows spec: pages first, then components, APIs, models, crosscutting
- [x] Slugs are generated from surface names (lowercase, hyphens, no special chars)
- [x] Each bean file has valid YAML frontmatter and all required body sections
- [x] `beans/_index.md` lists all generated beans with ID, title, type, status
- [x] `beans/_templates/` contains the template text files
- [x] Resume mode skips already-written beans (no overwrite)
- [x] Checkpoint occurs every N beans during generation
- [x] State checkpoint written after Stage E completion
- [x] Bean count is logged for progress tracking
- [x] Unit tests cover ordering, slug generation, resume skip, indexer output
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Implement writer.py — bean file generation | Developer | — | Done |
| 2 | Implement indexer.py — master index and templates dir | Developer | 1 | Done |
| 3 | Write unit tests for writer and indexer | Developer | 2 | Done |
| 4 | Quality gate — ruff, mypy, pytest | Tech QA | 3 | Done |

## Notes

- Depends on BEAN-020–BEAN-026 (analyzers produce surfaces), BEAN-028 (templates), BEAN-006 (state management).
- Reference: Spec sections 4.1 (Bean outputs), 6 Stage E (Bean generation), 8.1 (Bean naming), 9.2 (Checkpointing).
- The spec requires deterministic iteration: "The generator must iterate the entire worklist. Any skipped item must be recorded with reason."
- **BA Skip:** Requirements and acceptance criteria are fully specified in the bean — no ambiguity requiring BA analysis.
- **Architect Skip:** Design is straightforward — iterate SurfaceCollection (ordering built-in), call render_bean, write files, generate index. No cross-boundary or architectural decisions needed.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Implement writer.py | Developer | 10m | — | — |
| 2 | Implement indexer.py | Developer | 5m | — | — |
| 3 | Write unit tests | Developer | 10m | — | — |
| 4 | Quality gate | Tech QA | 5m | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 4 |
| **Total Duration** | 30m |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |

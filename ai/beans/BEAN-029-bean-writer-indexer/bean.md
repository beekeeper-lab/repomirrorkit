# BEAN-029: Bean Writer & Indexer (Stage E)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-029 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
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

- [ ] Bean files are written as `beans/BEAN-001-<slug>.md`, `BEAN-002-<slug>.md`, etc.
- [ ] Ordering follows spec: pages first, then components, APIs, models, crosscutting
- [ ] Slugs are generated from surface names (lowercase, hyphens, no special chars)
- [ ] Each bean file has valid YAML frontmatter and all required body sections
- [ ] `beans/_index.md` lists all generated beans with ID, title, type, status
- [ ] `beans/_templates/` contains the template text files
- [ ] Resume mode skips already-written beans (no overwrite)
- [ ] Checkpoint occurs every N beans during generation
- [ ] State checkpoint written after Stage E completion
- [ ] Bean count is logged for progress tracking
- [ ] Unit tests cover ordering, slug generation, resume skip, indexer output
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-020–BEAN-026 (analyzers produce surfaces), BEAN-028 (templates), BEAN-006 (state management).
- Reference: Spec sections 4.1 (Bean outputs), 6 Stage E (Bean generation), 8.1 (Bean naming), 9.2 (Checkpointing).
- The spec requires deterministic iteration: "The generator must iterate the entire worklist. Any skipped item must be recorded with reason."

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

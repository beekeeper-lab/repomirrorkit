# BEAN-055: Data-Model Relationships Report (with Mermaid ER Diagram)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-055 |
| **Status** | Approved |
| **Priority** | Medium |
| **Created** | 2026-05-01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The `analyze_models` analyzer (`src/repo_mirror_kit/harvester/analyzers/models.py`, ~951 LOC) extracts data models across multiple frameworks (Prisma, SQLAlchemy, Django, Entity Framework, etc.) and captures fields per model. What it does **not** capture in any consolidated form is the **relationships between models**: foreign keys, one-to-many cardinalities, cascade rules, and the overall shape of the schema. A developer recreating the project needs the schema topology, not just a list of tables. Without it, they have to rebuild relationships by inspecting each model bean individually — which is exactly the manual work the harvester exists to eliminate.

## Goal

After a successful harvest run, `<out>/data-model.md` contains:
1. A list of all models grouped by source framework, with each model's fields and relationships annotated
2. A Mermaid ER diagram showing all detected relationships (FKs, cardinalities)
3. A relationships table summarizing every detected FK with source-of-truth file references

`REQUIREMENTS.md` (BEAN-051) embeds the Mermaid diagram from this report under "Data Models."

## Scope

### In Scope
- New report module `src/repo_mirror_kit/harvester/reports/data_model.py` with a `write_data_model_report(surfaces: SurfaceCollection, output_dir: Path) -> Path` function
- Extend `ModelSurface` (or add a sibling type) to include relationship metadata: `relationships: list[ModelRelationship]` where `ModelRelationship` carries source-model, target-model, kind (one-to-one / one-to-many / many-to-many), FK column, cascade rule
- Extend `analyze_models` to populate relationships from each framework's idioms:
  - SQLAlchemy: `relationship()` and `ForeignKey(...)` declarations
  - Prisma: `@relation` and `@@id` blocks
  - Django: `ForeignKey`, `OneToOneField`, `ManyToManyField`
  - Entity Framework: navigation properties + `[ForeignKey]` annotations
- Generate Mermaid `erDiagram` syntax from the relationship graph
- Wire into Stage F (reports) via `pipeline.py:_run_stage_f`
- BEAN-051 (REQUIREMENTS.md) embeds the Mermaid block from `data-model.md` under "Data Models"
- Unit tests for relationship extraction per framework and Mermaid generation
- Integration test (BEAN-050) asserts the report exists when the fixture project has models

### Out of Scope
- Migration generation (extracting `migrations/` directory contents) — separate concern
- Indexes, constraints beyond FKs (CHECK constraints, partial indexes) — separate concern
- ORM-specific type-mapping reverse engineering — separate concern

## Acceptance Criteria

- [ ] After a harvest run, `<out>/data-model.md` exists when models are detected
- [ ] The report includes every detected model with its fields
- [ ] The report includes a Mermaid `erDiagram` block that compiles in a Mermaid renderer (validated via a syntax test)
- [ ] The report includes a relationships table with source/target/kind/FK column/cascade for every detected relationship
- [ ] `ModelSurface` (or sibling type) carries relationship metadata
- [ ] `REQUIREMENTS.md` embeds the Mermaid block when BEAN-051 + this bean are both merged
- [ ] Unit tests cover relationship extraction for at least 2 frameworks
- [ ] Integration test asserts the report exists for fixture projects with models
- [ ] Lint, type-check, and pytest all clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Goal alignment" item 6 (2026-05-01)
- Depends on BEAN-050 (integration test) for safety net
- Soft-coupled to BEAN-051: this bean is independently valuable, but the Mermaid embedding in REQUIREMENTS.md only happens once both are merged. Order: BEAN-051 first to anchor the link, then BEAN-055 fills it in.
- Soft-coupled to BEAN-057 (split models analyzer): if BEAN-057 lands first, this bean's relationship extraction lives cleanly in the per-framework submodules. If this bean lands first, BEAN-057 has more to migrate. Either order works.
- Architect should weigh in on whether relationships belong on `ModelSurface` itself or as a separate `RelationshipSurface` type

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

# BEAN-023: Model & Entity Analyzer

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-023 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester needs to extract data models and entities — their fields, types, relationships, and persistence mechanisms — to generate model beans and build the APIs→models traceability map. Models are defined differently across ORMs (Prisma, SQLAlchemy, Entity Framework) and plain SQL migrations.

## Goal

Implement a model/entity analyzer that discovers data models across detected data layer technologies, producing `ModelSurface` objects with entity names, fields, relationships, and persistence references.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/analyzers/models.py`
- Model extraction strategies per detected data technology:
  - **Prisma**: Parse `schema.prisma` for model definitions, fields, relations
  - **SQLAlchemy**: Parse Python files for `class Model(Base)` patterns, `Column()`, `relationship()`
  - **Entity Framework**: Parse C# files for `DbSet<>` properties, entity class definitions
  - **TypeORM/Sequelize**: Parse TypeScript/JavaScript model files with decorator patterns
  - **Plain SQL**: Parse `.sql` migration files for `CREATE TABLE` statements, extract columns
  - **Alembic**: Parse migration files for `op.create_table()`, `op.add_column()` etc.
- Extract: entity name, fields (name + type + constraints), relationships (FK, 1:N, N:M), persistence refs (table name, migration files)
- Populate `ModelSurface` objects
- Unit tests per data technology

### Out of Scope
- Database connection or runtime schema introspection
- Index and performance analysis
- Data validation rules beyond column constraints
- NoSQL document model extraction

## Acceptance Criteria

- [ ] Extracts models from Prisma schema files
- [ ] Extracts models from SQLAlchemy model classes
- [ ] Extracts models from Entity Framework entity classes
- [ ] Extracts models from SQL `CREATE TABLE` statements
- [ ] Each model produces a `ModelSurface` with entity name, fields, relationships, source ref
- [ ] Fields include name, type, and constraint hints (nullable, unique, primary key)
- [ ] Relationships are identified (foreign keys, references)
- [ ] Persistence references (table names, migration files) are captured
- [ ] Analyzer only runs for detected data technologies
- [ ] Unit tests cover each data technology extraction
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-009, BEAN-010, BEAN-019.
- Reference: Spec section 6, Stage C (Models/entities and their fields).
- Coverage gate: `models.with_bean / models.total >= 0.95` (spec section 7.2).

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

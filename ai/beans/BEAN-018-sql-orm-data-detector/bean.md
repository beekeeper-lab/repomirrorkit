# BEAN-018: SQL/ORM Data Detector

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-018 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester needs to detect data layer technologies — ORMs, migration tools, and database schemas — to activate model and entity analyzers. Data layer detection spans multiple ecosystems: Prisma (Node), SQLAlchemy/Alembic (Python), Entity Framework (.NET), Flyway/Liquibase (Java/general), and plain SQL migrations.

## Goal

Implement a data detector that identifies ORM frameworks, migration tools, and schema definition files across multiple ecosystems.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/detectors/data.py`
- Detect data layer via:
  - Prisma: `prisma/schema.prisma`, `@prisma/client` in `package.json`
  - SQLAlchemy: `sqlalchemy` in Python dependencies, model files with `Column`, `relationship`
  - Alembic: `alembic/` directory, `alembic.ini`
  - Entity Framework: `*.csproj` with `Microsoft.EntityFrameworkCore`, `Migrations/` directory
  - Flyway: `flyway.conf`, `sql/` or `db/migration/` directories
  - Liquibase: `liquibase.properties`, `db/changelog/` directories
  - Plain SQL: `migrations/` directories with `.sql` files
  - ORM model patterns: `*.model.ts`, `models.py`, model class definitions
- Signal includes which specific data tool(s) detected
- Confidence scoring and evidence collection
- Register with detector framework
- Unit tests

### Out of Scope
- Actual model/entity extraction (BEAN-023)
- Schema parsing or field extraction
- NoSQL (MongoDB, DynamoDB) detection — could be added later
- Database connection testing

## Acceptance Criteria

- [ ] `DataDetector` implements the `Detector` interface
- [ ] Detects Prisma via schema file and package.json dependency
- [ ] Detects SQLAlchemy via Python dependency and model patterns
- [ ] Detects Alembic via directory structure and config file
- [ ] Detects Entity Framework via .csproj dependency and migrations
- [ ] Detects Flyway and Liquibase via config files and directory structure
- [ ] Detects plain SQL migrations via directory patterns
- [ ] Signal includes specific tool names detected
- [ ] Confidence scoring based on evidence strength
- [ ] Unit tests cover: Prisma repo, SQLAlchemy repo, EF repo, plain SQL repo, no-data repo
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-010 (Detector Framework).
- Reference: Spec section 2.1 (Data: SQL migrations, Prisma/EF/Flyway/Liquibase, ORM models, plain SQL).
- This detector is cross-ecosystem — it checks Node, Python, and .NET data patterns in one detector.

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

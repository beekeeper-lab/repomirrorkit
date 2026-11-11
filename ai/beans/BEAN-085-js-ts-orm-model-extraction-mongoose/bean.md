# BEAN-085: JS/TS ORM Model Extraction (Mongoose, Drizzle, Sequelize define, Knex)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-085 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-11-11 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

TS/JS apps outside Prisma/TypeORM decorators and plain interfaces get no `ModelSurface` (Mongoose `new Schema({...})`, Drizzle `pgTable(...)`, Sequelize `define`/`init`). Without models there is no DB design bundle, no field mapping and no invariants for those stacks.

## Goal

Add per-framework extractors under `analyzers/models/` using tree-sitter; register them by stack detection; feed DB design and screen mapping.

## Acceptance Criteria

- [ ] One fixture per ORM yields models with fields/constraints/relations
- [ ] DB design bundle loads into SQLite for each fixture
- [ ] Screen field->model mapping works against them
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: real-world triage of the microblog app (`docs/real-world-triage-microblog.md`), 2026-11-11.

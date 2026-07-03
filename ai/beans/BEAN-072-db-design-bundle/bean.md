# BEAN-072: DB Design Bundle — SQL DDL + JSON Schema + Seed Data

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-072 |
| **Status** | Unapproved |
| **Priority** | Medium |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

`data-model.md` (BEAN-055) gives humans a Mermaid ER diagram, but a rebuild agent needs the *executable* form of the data design: DDL it can adapt to the target stack, per-entity JSON Schema it can validate against, and the seed data the app requires to boot. Mermaid is a rendering, not a source of truth.

## Goal

Stage G emits `<out>/db-design/`: `schema.sql` (portable DDL), `entities/<Entity>.schema.json` (JSON Schema per entity), and `seed-data.sql`/`seed-data.json` — generated from `ModelSurface` + relationships + (when available) BEAN-065 constraints and BEAN-066 seed datasets. The existing Mermaid ER diagram is regenerated from this same data.

## Scope

### In Scope
- `generator/db_design.py`: models → ANSI-leaning DDL (tables, columns, PK/FK, NOT NULL/UNIQUE; CHECK constraints when BEAN-065 rules exist); dialect quirks noted as comments, not silently dropped
- JSON Schema per entity (types, required, enum values from BEAN-066 where linked)
- Seed data emission from `SeedDataSurface`s (when BEAN-066 has landed; otherwise section omitted with a gap note)
- `db-design/README.md` index; REQUIREMENTS.md + data-model.md link the bundle
- Round-trip sanity test: generated `schema.sql` loads into SQLite (or documented dialect-skips)

### Out of Scope
- Migration history reconstruction (final-state schema only)
- NoSQL data stores (future bean)
- Index tuning beyond declared indexes

## Acceptance Criteria

- [ ] Fixture harvest emits `db-design/` with DDL covering every detected model, executable against SQLite in tests
- [ ] FKs and cardinalities in DDL match `relationship_details`
- [ ] Every entity has a JSON Schema whose fields match the model surface
- [ ] Constraint/seed sections appear when their source surfaces exist, with gap notes when not
- [ ] Mermaid ER output remains consistent with the DDL (single data source)
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track C
- Wave 2 — no hard deps (models already extracted); soft deps: BEAN-065 (CHECK constraints), BEAN-066 (seed data). Design for their absence
- Feeds BEAN-078 (schema-diff parity check)

# BEAN-066: `SeedDataSurface` — Enums, Lookup Tables, Fixtures, Migration Seeds

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-066 |
| **Status** | Unapproved |
| **Priority** | Medium |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Apps don't run on schema alone: an empty `order_status` lookup table, missing role enum values, or absent default admin account makes a rebuilt app non-functional. No analyzer captures reference/seed data today, so a rebuild agent has no way to know these values exist, let alone what they are.

## Goal

A `SeedDataSurface` capturing enumerations and seed/reference datasets: code-level enums, DB lookup-table inserts, fixture files, and migration data steps — with actual values, not just names.

## Scope

### In Scope
- `SeedDataSurface` dataclass: `dataset_name`, `kind` (`enum` | `lookup_table` | `fixture` | `migration_seed`), `values: list[dict]`, `target_model_ref`, `source_ref`
- Code enums: Python `Enum`/`StrEnum` subclasses (stdlib `ast`); TS `enum` + `as const` object literals (regex acceptable v1; upgrade under BEAN-061 later)
- Migration seeds: `INSERT INTO` statements in migration/SQL files; Alembic `op.bulk_insert`; Prisma seed scripts
- Fixture files: `fixtures/*.json|yaml`, Django fixtures — recorded with row counts + sample values (cap stored values per dataset, note truncation)
- Link datasets to `ModelSurface`s by table/model name
- Bean renderer; values tables in the bean; fixtures extended with a lookup table + enum

### Out of Scope
- Production data extraction (only what's committed to the repo)
- Binary/BLOB seed content

## Acceptance Criteria

- [ ] A Python `StrEnum` in the fixture yields a `SeedDataSurface` with all member values
- [ ] A migration `INSERT` yields a `lookup_table` dataset with the inserted rows
- [ ] Datasets link to their model surface when resolvable
- [ ] Value lists are capped with explicit truncation notes (no silent loss)
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track A
- Wave 1 — no hard dependencies
- Feeds BEAN-072 (DB design bundle includes seed data)

# BEAN-083: SQLAlchemy Association Tables and Core `Table(...)` Definitions

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-083 |
| **Status** | Unapproved |
| **Priority** | Medium |
| **Created** | 2026-11-11 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Many-to-many links in SQLAlchemy are often declared as `sa.Table('followers', metadata, Column(...))` rather than model classes (microblog's followers). They are invisible to the model analyzer, so the DDL and ER diagram miss a table and the follower relationship's join shape.

## Goal

Extract Core `Table()` definitions (columns, FKs, composite PKs) as association/data tables and wire them into `relationship(secondary=...)` details and the DB design bundle.

## Acceptance Criteria

- [ ] `followers` appears in data-model.md, schema.sql and entity schemas for the microblog repo
- [ ] Many-to-many relationships carry `secondary` table in `relationship_details`
- [ ] DDL has composite primary key and both FKs
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: real-world triage of the microblog app (`docs/real-world-triage-microblog.md`), 2026-11-11.

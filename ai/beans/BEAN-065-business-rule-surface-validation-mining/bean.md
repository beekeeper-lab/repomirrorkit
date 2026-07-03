# BEAN-065: `BusinessRuleSurface` — Validation & Constraint Mining

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-065 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Business rules — validation constraints, permission checks, calculations, invariants — *are* the requirements; everything else is scaffolding. No analyzer extracts them. A rebuilt app that accepts a negative quantity or skips an ownership check is not a functional replacement, yet today's beans say nothing about either.

## Goal

A `BusinessRuleSurface` populated from declarative sources (validation libraries, DB constraints, decorators/guards), each rule linked to the surface it protects and stated framework-neutrally.

## Scope

### In Scope
- `BusinessRuleSurface` dataclass: `rule_kind` (`validation` | `permission` | `invariant` | `calculation`), `expression` (human-readable, framework-neutral), `applies_to` (surface refs), `source_ref`, `confidence`
- Python (stdlib `ast`): Pydantic `Field(...)` constraints + `@validator`/`@field_validator`; marshmallow validators; Django model validators/`Meta.constraints`
- JS/TS (tree-sitter, BEAN-061): zod/yup/joi schema chains (`.min()`, `.email()`, `.required()`...); NestJS guards + `class-validator` decorators
- DB constraints: CHECK/UNIQUE/NOT NULL from SQL DDL + SQLAlchemy/Prisma/TypeORM declarations (extends the per-framework model analyzers)
- Permission mining: route-level auth decorators/middleware (`@login_required`, role guards) → `permission` rules attached to routes/APIs
- Bean renderer + Rules section per affected surface's bean; fixtures extended with representative rules

### Out of Scope
- Imperative business-logic mining from arbitrary function bodies (agentic enrichment's job — BEAN-068 records these with lower confidence)
- Cross-service invariants

## Acceptance Criteria

- [ ] Both fixtures yield ≥3 business rules each spanning ≥2 `rule_kind`s
- [ ] A zod/Pydantic constraint appears as a framework-neutral expression (e.g. "quantity: integer, minimum 1") not library syntax
- [ ] Each rule links to ≥1 existing surface (`applies_to` resolves)
- [ ] DB constraints from the models feed the same surface type (single rules inventory)
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track A
- Wave 2 — hard dep: BEAN-061 for JS/TS; Python portion can start in Wave 1 if split
- Feeds BEAN-072 (DB bundle) and BEAN-074 (Gherkin scenarios from rules)

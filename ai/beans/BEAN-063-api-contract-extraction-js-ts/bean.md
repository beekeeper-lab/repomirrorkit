# BEAN-063: API Contract Extraction — JS/TS Stacks

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-063 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Same gap as BEAN-062 for the JavaScript/TypeScript ecosystem (Express, Fastify, NestJS, Next.js API routes): endpoints are detected, contracts are empty. TS is the highest-value target because type annotations and DTO classes carry declared contracts — richer signal than Python duck typing.

## Goal

Express/Fastify/NestJS/Next.js API surfaces get populated `request_schema`/`response_schema` extracted via the tree-sitter foundation (BEAN-061), using the same schema shape and `confidence` markers as BEAN-062.

## Scope

### In Scope
- NestJS: DTO classes on `@Body()`/`@Query()`/`@Param()`; return types; `class-validator` decorators feed `required`/constraints
- Express/Fastify: `req.body.X`/`req.query.X` property accesses → inferred request fields; `res.json({...})` object literals → inferred response fields; Fastify JSON-schema route options → declared contracts (highest confidence)
- Next.js: route-handler `Request`/`Response` usage and exported types
- TS interface/type-alias resolution within the repo (single-hop import following)
- Extend the `ts-next` fixture with typed endpoints; unit + integration assertions

### Out of Scope
- .NET contracts (follow-up bean once patterns are proven twice)
- GraphQL schemas (distinct surface type; future bean)
- Full type-system evaluation (generics, mapped types) — record as `unknown` gaps

## Acceptance Criteria

- [ ] Harvesting the `ts-next` fixture yields ≥1 API surface with non-empty request AND response schemas
- [ ] Fastify schema-option routes produce `declared`-confidence contracts matching the JSON schema
- [ ] NestJS DTO fields include validator-derived `required`/constraint info
- [ ] Schema shape is byte-compatible with BEAN-062's (shared helper/type, not a parallel format)
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track A
- Wave 2 — hard dep: BEAN-061. Shares schema-shape helper with BEAN-062 (land 062 first)

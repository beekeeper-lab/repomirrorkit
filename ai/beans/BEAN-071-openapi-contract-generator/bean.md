# BEAN-071: OpenAPI 3.1 Contract Generator

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-071 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

API behavior is currently described only in per-bean Markdown. Rebuild agents (and contract-test tooling) consume OpenAPI natively: it is the machine-readable, framework-neutral, industry-standard representation of an API surface. Once BEAN-062/063 populate contracts, not emitting OpenAPI would leave the highest-leverage design artifact on the table.

## Goal

Stage G emits `<out>/api-contract.yaml` — a valid OpenAPI 3.1 document covering every API surface: paths, methods, parameters, request/response schemas, auth requirements — with gaps explicitly marked.

## Scope

### In Scope
- `generator/openapi.py`: `ApiSurface` collection → OpenAPI 3.1 (paths from `path`/`method`, `requestBody`/`responses` from populated schemas, `security` from auth requirements + AuthSurface-derived scheme)
- Shared model schemas hoisted to `components/schemas` (dedupe by entity where request/response shapes match `ModelSurface`s)
- Unknown contracts → documented empty schema + `x-harvester-gap: true` extension (visible, machine-filterable — never fabricated shapes)
- `x-harvester-confidence` extension per operation
- Validation in tests via an OpenAPI validator (dev dependency)
- REQUIREMENTS.md links the contract; RUNBOOK notes how to serve it (e.g. Swagger UI)

### Out of Scope
- GraphQL/gRPC IDL (future beans)
- Generating server stubs from the contract (rebuild agent's job)

## Acceptance Criteria

- [ ] Fixture harvest emits `api-contract.yaml` that passes OpenAPI 3.1 validation
- [ ] Every detected API surface appears as a path+method; populated schemas round-trip field names/types/required
- [ ] Gap operations carry `x-harvester-gap` and count is reported in coverage output
- [ ] Auth-protected endpoints carry a `security` requirement
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track C
- Wave 2 — hard dep: BEAN-062 (populated Python contracts); BEAN-063 extends coverage when it lands
- Part of the recommended first vertical slice (062 → 071 → 076)
- Feeds BEAN-078 (golden replay validates against this contract)

# BEAN-028: Bean Templates

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-028 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester generates requirement beans from extracted surfaces. Each bean type (page, component, API, model, auth, config, crosscutting) has a distinct template with specific required sections defined in the spec. These templates must be implemented as code that renders surface data into well-formed markdown beans with YAML frontmatter.

## Goal

Implement bean template definitions for all 7 bean types, each producing correctly structured markdown with the required frontmatter and body sections from the spec.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/beans/templates.py`
- Define template rendering functions for all 7 bean types:
  - **Page/Route bean**: Overview, User stories, Functional requirements, UI elements, Data & API interactions, Validation & error states, Acceptance criteria, Open questions
  - **Component bean**: Purpose, Props/inputs contract, Outputs/events, States, Usage locations, Acceptance criteria
  - **API bean**: Endpoints, Auth, Request schema, Response schema, Errors, Side effects, Acceptance criteria, Examples
  - **Model bean**: Entity description, Fields, Relationships, Persistence, Validation rules, Acceptance criteria
  - **Auth bean**: Roles/permissions/rules, Protected routes/endpoints map, Token/session assumptions, Acceptance criteria
  - **Config bean**: Env vars + defaults, Feature flags, Required external services, Acceptance criteria
  - **Crosscutting bean**: Concern-specific sections per spec 8.9
- YAML frontmatter generation per spec section 8.2: id, type, title, source_refs, traceability, status
- Templates accept `Surface` objects and render to markdown strings
- Store template text in `beans/_templates/` in the output directory (spec section 4.1)
- Unit tests for each template rendering with sample surface data

### Out of Scope
- Actually writing beans to disk (BEAN-029)
- Bean indexing and ordering (BEAN-029)
- Surface extraction (BEAN-020 through BEAN-026)

## Acceptance Criteria

- [ ] Template functions exist for all 7 bean types
- [ ] Each template produces markdown with valid YAML frontmatter (id, type, title, source_refs, traceability, status)
- [ ] Page/Route template includes all 8 required sections from spec 8.3
- [ ] Component template includes all 6 required sections from spec 8.4
- [ ] API template includes all 8 required sections from spec 8.5
- [ ] Model template includes all 6 required sections from spec 8.6
- [ ] Auth template includes all 4 required sections from spec 8.7
- [ ] Config template includes all 4 required sections from spec 8.8
- [ ] Crosscutting template includes sections per spec 8.9
- [ ] Templates are rendered from `Surface` dataclass instances
- [ ] Generated beans have `status: draft` in frontmatter
- [ ] Unit tests verify each template renders correctly with sample data
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-019 (Surface Data Model) for the input types.
- Reference: Spec sections 8.1–8.9 (Bean templates — all sections).
- The spec says templates should also be checked in to `beans/_templates/` in the output directory.

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

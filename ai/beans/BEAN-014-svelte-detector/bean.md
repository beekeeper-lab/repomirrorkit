# BEAN-014: Svelte Detector

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-014 |
| **Status** | Approved |
| **Priority** | Medium |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester needs to detect Svelte/SvelteKit projects to activate Svelte-specific analyzers. Svelte uses `.svelte` files and SvelteKit has a file-based routing system similar to Next.js.

## Goal

Implement a basic Svelte detector that identifies Svelte and SvelteKit projects by examining dependencies, `.svelte` files, and SvelteKit configuration.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/detectors/svelte.py`
- Detect Svelte via:
  - `svelte` in `package.json` dependencies
  - Presence of `.svelte` files
  - `svelte.config.js` or `svelte.config.ts` presence
  - `@sveltejs/kit` dependency for SvelteKit detection
  - `src/routes/` directory structure (SvelteKit file-based routing)
- Basic detection for v1
- Confidence scoring and evidence collection
- Register with detector framework
- Unit tests

### Out of Scope
- Deep SvelteKit adapter analysis
- Svelte 4 vs 5 differentiation
- Server-side rendering specifics

## Acceptance Criteria

- [ ] `SvelteDetector` implements the `Detector` interface
- [ ] Detects Svelte via `package.json` dependency
- [ ] Detects Svelte via `.svelte` file presence
- [ ] Detects SvelteKit via config and `@sveltejs/kit` dependency
- [ ] Confidence scoring based on evidence strength
- [ ] No false positives on React or Vue projects
- [ ] Unit tests cover: Svelte repo, SvelteKit repo, non-Svelte repo
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-010 (Detector Framework).
- Spec marks SvelteKit as "basic" support for v1.
- Reference: Spec section 2.1.

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

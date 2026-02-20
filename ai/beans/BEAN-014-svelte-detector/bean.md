# BEAN-014: Svelte Detector

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-014 |
| **Status** | Done |
| **Priority** | Medium |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
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

- [x] `SvelteDetector` implements the `Detector` interface
- [x] Detects Svelte via `package.json` dependency
- [x] Detects Svelte via `.svelte` file presence
- [x] Detects SvelteKit via config and `@sveltejs/kit` dependency
- [x] Confidence scoring based on evidence strength
- [x] No false positives on React or Vue projects
- [x] Unit tests cover: Svelte repo, SvelteKit repo, non-Svelte repo
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Implement SvelteDetector class | Developer | BEAN-010 | Done |
| 2 | Write unit tests (19 tests) | Developer | 1 | Done |
| 3 | Run ruff check + format | Tech-QA | 2 | Done |
| 4 | Run mypy strict mode | Tech-QA | 2 | Done |
| 5 | Run pytest + verify ACs | Tech-QA | 2 | Done |

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

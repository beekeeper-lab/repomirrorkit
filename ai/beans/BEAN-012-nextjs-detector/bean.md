# BEAN-012: Next.js Detector

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-012 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | 2026-02-15 |
| **Completed** | 2026-02-15 |
| **Duration** | ~30 min |
| **Owner** | Claude |
| **Category** | App |

## Problem Statement

Next.js projects have a distinct file-based routing system and specific configuration files that differ from plain React. The harvester needs to detect Next.js specifically to activate file-based route discovery (pages/ or app/ directory) and API route detection (pages/api/ or app/api/).

## Goal

Implement a Next.js detector that identifies Next.js projects by examining configuration files, directory structure, and dependencies, producing a confidence-scored signal.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/detectors/nextjs.py`
- Detect Next.js via:
  - `next` in `package.json` dependencies
  - `next.config.js`, `next.config.mjs`, or `next.config.ts` presence
  - `pages/` or `app/` directory structure with route-like files
  - `pages/api/` or `app/api/` directory for API routes
  - Next.js-specific imports: `next/router`, `next/link`, `next/image`
- Higher specificity than React detector — Next.js implies React but not vice versa
- Confidence scoring based on number and strength of signals
- Register with the detector framework
- Unit tests with sample inventory data

### Out of Scope
- Actual route extraction from pages/app directories (BEAN-020)
- API endpoint extraction (BEAN-022)
- Middleware or edge runtime detection

## Acceptance Criteria

- [x] `NextjsDetector` implements the `Detector` interface
- [x] Detects Next.js via `package.json` dependency check
- [x] Detects Next.js via `next.config.*` file presence
- [x] Detects Next.js via `pages/` or `app/` directory structure
- [x] Detects Next.js API routes via `pages/api/` or `app/api/`
- [x] Confidence score reflects evidence strength
- [x] Evidence list includes triggering files/paths
- [x] Registered in the detector registry
- [x] No false positives on plain React or Vue projects
- [x] Unit tests cover: Next.js repo, plain React repo (no match), partial signals
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Implement NextjsDetector in nextjs.py | Developer | BEAN-010 | Done |
| 2 | Write unit tests (37 tests, 8 classes) | Tech-QA | 1 | Done |
| 3 | QA verification (ruff, mypy, pytest) | Tech-QA | 1, 2 | Done |

## Notes

- Depends on BEAN-010 (Detector Framework).
- Reference: Spec section 2.1 (Target repo types — "Next.js").

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

# BEAN-012: Next.js Detector

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-012 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
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

- [ ] `NextjsDetector` implements the `Detector` interface
- [ ] Detects Next.js via `package.json` dependency check
- [ ] Detects Next.js via `next.config.*` file presence
- [ ] Detects Next.js via `pages/` or `app/` directory structure
- [ ] Detects Next.js API routes via `pages/api/` or `app/api/`
- [ ] Confidence score reflects evidence strength
- [ ] Evidence list includes triggering files/paths
- [ ] Registered in the detector registry
- [ ] No false positives on plain React or Vue projects
- [ ] Unit tests cover: Next.js repo, plain React repo (no match), partial signals
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

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

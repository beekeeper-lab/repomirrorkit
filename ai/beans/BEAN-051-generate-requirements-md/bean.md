# BEAN-051: Generate Top-Level `REQUIREMENTS.md` Aggregator

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-051 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-05-01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester's stated goal is to take a Git repository and produce a list of requirements sufficient to recreate the project. Today, the output is **fragmented**: hundreds of per-surface beans under `<out>/beans/`, plus per-stage reports (`coverage`, `gaps`, `traceability`, `surface_map`), plus a Stage G Claude Code project scaffold. There is no single artifact a user can hand to another developer (or feed into Claude) and say "build this from scratch." This is the central goal-alignment gap identified in the code review: the analytical work is solid, but the *delivery* of the work is not yet packaged as requirements. A user receiving 300 markdown files in a directory cannot easily extract "what does this project do" from them.

## Goal

After a successful harvest run, the output directory contains a single top-level `REQUIREMENTS.md` that consolidates the surface analysis into a human- and AI-consumable specification. The document is organized by domain (Routes/Pages, APIs, Data Models, Auth, Background Jobs, Integrations, Build & Deploy, Tests) with each section listing the surfaces with one-line summaries and deep links into the per-bean detail files. A reader can skim the file in five minutes and get a complete picture of what would need to be built to recreate the project.

## Scope

### In Scope
- New module `src/repo_mirror_kit/harvester/generator/requirements_md.py` containing a `generate_requirements_md(surfaces: SurfaceCollection, profile: StackProfile, output_dir: Path) -> str` function
- Document structure:
  - Front matter: project name, harvest date, harvester version, source repo URL/ref, total bean count
  - "Tech Stack" section (derived from `StackProfile`)
  - "Functional Requirements" section grouped by surface type (Routes, APIs, Models, Auth, etc.) — each surface gets one row in a table with name, source file, one-line description, and a relative link to its bean
  - "Cross-Cutting Concerns" section
  - "Build & Deploy Targets" section
  - "Testing Approach" section
  - Footer linking to `coverage.md`, `gaps.md`, `surface-map.json`
- Wire the new generator into Stage G via `harvester/generator/assembler.py`, writing to `<out>/REQUIREMENTS.md` (top-level, not nested under `project-folder/`)
- Add a unit test in `tests/unit/test_requirements_md.py` that validates structure on a synthetic `SurfaceCollection`
- Update the integration test from BEAN-050 to assert `REQUIREMENTS.md` exists and contains the expected sections

### Out of Scope
- Behavioral content (intent, acceptance criteria) — that arrives via BEAN-054 (behavioral analyzer) and LLM enrichment; this bean produces structural-only content
- Mermaid diagrams — addressed for data models in BEAN-055
- Cross-linking to upstream issue trackers — separate concern
- Generating per-surface deep prose — keep each surface row concise; detail lives in the bean

## Acceptance Criteria

- [ ] After a successful harvest run, `<out>/REQUIREMENTS.md` exists
- [ ] The file contains a Tech Stack section listing all detected stacks
- [ ] The file contains separate sections for Routes/Pages, APIs, Data Models, Auth, Config, Cross-Cutting, Build/Deploy, Testing — each present even if empty (with a "(none detected)" note)
- [ ] Every surface listed in the file has a working relative link to its corresponding bean file
- [ ] Total bean count in the front matter matches the count in `_index.md`
- [ ] Unit test validates structure for a synthetic `SurfaceCollection`
- [ ] Integration test (BEAN-050) verifies `REQUIREMENTS.md` is generated for fixture projects
- [ ] Lint, type-check, and pytest all clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Goal alignment" item 1 (2026-05-01)
- This is the **single most important goal-alignment bean**. Everything else in the goal-alignment slice (BEAN-052 .env.example, BEAN-053 RUNBOOK.md, BEAN-054 behavioral analyzer, BEAN-055 data-model report) either feeds into this file or sits alongside it.
- Depends on BEAN-050 (integration test) for safety net
- Architect should decide where the file sits: top-level of `<out>/` (recommended) vs inside `project-folder/`. Recommendation: top-level so it's the first thing a user sees in the output directory.

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

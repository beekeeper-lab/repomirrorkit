# BEAN-053: Generate `RUNBOOK.md` from Build/Deploy Surfaces

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-053 |
| **Status** | Approved |
| **Priority** | Medium |
| **Created** | 2026-05-01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The `analyze_build_deploy` analyzer (`src/repo_mirror_kit/harvester/analyzers/build_deploy.py`, ~664 LOC) already detects how a project is built, run, and deployed: package.json scripts, Makefile targets, Dockerfile build/run commands, CI YAML jobs, deploy scripts. This information is captured in `BuildDeploySurface` instances but is not aggregated into a runnable form. A developer recreating the project needs to know: "How do I install dependencies? How do I start the dev server? How do I run tests? How do I build for production? How do I deploy?" Today they have to crawl multiple beans to assemble this picture, even though the analyzer has already collected the answers.

## Goal

After a successful harvest run, `<out>/RUNBOOK.md` contains a single-page operational guide listing the canonical commands for: install, dev/run, test, lint, build, and deploy. Each command is sourced from a real artifact in the analyzed repo (package.json, Makefile, Dockerfile, etc.) with a citation. A developer recreating the project can use this file as a checklist of what scripts the recreated project must support.

## Scope

### In Scope
- New module `src/repo_mirror_kit/harvester/generator/runbook_md.py` containing a `generate_runbook_md(surfaces: SurfaceCollection, output_dir: Path) -> Path` function
- Document structure with one section per operation kind:
  - **Install** — package manager bootstrap (`npm install`, `uv sync`, `pip install -e .`, etc.)
  - **Dev / Run** — start a local dev server or main entry point
  - **Test** — run the test suite
  - **Lint / Format** — code-quality tools
  - **Build** — produce a release artifact (build for prod, Docker image, wheel, etc.)
  - **Deploy** — deploy/release scripts if present
- For each section, list every detected command with a citation (e.g. `# from package.json:scripts.dev`)
- If a section has no detected commands, include a "(none detected — recreated project should still provide one)" placeholder so the recreator knows the gap
- Wire into Stage G via `harvester/generator/assembler.py`
- Add a unit test in `tests/unit/test_runbook_md.py`
- Update BEAN-050 integration test to assert `RUNBOOK.md` exists for fixture projects
- Reference `RUNBOOK.md` from `REQUIREMENTS.md` (BEAN-051) under "Build & Deploy"

### Out of Scope
- Validating that the listed commands actually work (would require running them — defer)
- Generating new build/run scripts for the recreated project (the file is a recipe, not a generator)
- CI matrix expansion or environment-specific variants

## Acceptance Criteria

- [ ] After a successful harvest run, `<out>/RUNBOOK.md` exists
- [ ] The file contains sections for Install, Dev/Run, Test, Lint, Build, Deploy (each present even if empty)
- [ ] Every command in the file has a citation pointing back to the source file
- [ ] Empty sections are marked clearly so a recreator knows what gaps exist
- [ ] Unit test validates structure and citation format on a synthetic surface set
- [ ] Integration test asserts `RUNBOOK.md` is generated for fixture projects with build/deploy surfaces
- [ ] Lint, type-check, and pytest all clean

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Source: `REVIEW_NOTES.md` §"Goal alignment" item 7 (2026-05-01)
- Sibling: BEAN-052 (.env.example). Same pattern, different analyzer source. Independent beans because they touch separate code paths and ship independently valuable artifacts.
- DevOps/Release Engineer should review the section taxonomy — there may be operations specific to certain stacks (e.g. database migrations) worth surfacing
- Independent of BEAN-051; BEAN-051 should link to `RUNBOOK.md` once both exist

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

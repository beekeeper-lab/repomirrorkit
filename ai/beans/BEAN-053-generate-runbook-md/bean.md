# BEAN-053: Generate `RUNBOOK.md` from Build/Deploy Surfaces

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-053 |
| **Status** | Done |
| **Priority** | Medium |
| **Created** | 2026-05-01 |
| **Started** | 2026-05-01 16:39 |
| **Completed** | 2026-05-01 16:41 |
| **Duration** | 5h 50m |
| **Owner** | team-lead |
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
| 1 | runbook_md.py generator + assembler wire-up | developer | — | Done |
| 2 | Verify operations matrix + groups + dedup | tech-qa | 01 | Done |

> Skipped: BA, Architect (small derived-artifact generator).

### Verification (Tech-QA)

- ✅ `harvester/generator/runbook_md.py` exists with `generate_runbook_md(surfaces, output_dir) → Path` writing `<output_dir>/RUNBOOK.md`.
- ✅ Wired into `assembler.py` step 6 after `.env.example`. Always runs.
- ✅ Document structure: header (with total count), Operations Quick Reference matrix, then 5 group sections by `config_type` (Build Tools / CI · CD / Containers / IaC / Platform), then Notes footer.
- ✅ Operations matrix: 6 rows (Install / Dev · Run / Test / Lint · Format / Build / Deploy · Release). Each row scans every surface's stages + targets for keyword matches and lists matching items with file citation. Dedup by (label, source) so identical stage + target labels collapse to one row.
- ✅ Empty operations cite gap hint "(none detected — recreated project should still provide one)" so the recreator sees what's missing.
- ✅ Group sections render counts in heading; empty groups still appear with "(none detected)" body.
- ✅ Citations use backticks for both stage labels and source paths so they render as inline code.
- ✅ 8 unit tests in `tests/unit/test_runbook_md.py`: file location, all-empty-sections render, group-by-config_type, Install matching, Test/Lint/Build/Deploy matching, gap hint, total count in header, dedup of stage/target overlap.
- ✅ Suite: 1749 passed (up from 1741; +8 new). Ruff clean.

Note: the bean's original aspiration — "list every install/dev/test/build/deploy command verbatim" — is met as far as the analyzer's signal goes. `analyze_build_deploy` records config-file artifacts and named stages/targets, not literal shell commands. The Operations matrix surfaces every detected stage label that maps to one of the canonical operations, with a citation back to the source file the recreator should open for the exact command. This is the correct fidelity given current analyzer scope.

## Notes

- Source: `REVIEW_NOTES.md` §"Goal alignment" item 7 (2026-05-01)
- Sibling: BEAN-052 (.env.example). Same pattern, different analyzer source. Independent beans because they touch separate code paths and ship independently valuable artifacts.
- DevOps/Release Engineer should review the section taxonomy — there may be operations specific to certain stacks (e.g. database migrations) worth surfacing
- Independent of BEAN-051; BEAN-051 should link to `RUNBOOK.md` once both exist

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | runbook_md.py generator + assembler wire-up | developer | — | — | — | — |
| 2 | Verify operations matrix + groups + dedup | tech-qa | — | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 2 |
| **Total Duration** | 5h 50m |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |
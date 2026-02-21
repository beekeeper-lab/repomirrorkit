# BEAN-037: CLAUDE.md Generator (Stage G)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-037 |
| **Status** | Done |
| **Priority** | High |
| **Created** | 2026-02-20 |
| **Started** | 2026-02-21 00:32 |
| **Completed** | 2026-02-21 00:43 |
| **Duration** | 11m |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester produces beans (individual requirements), surface maps, traceability reports, and coverage analysis — but the ultimate goal of RepoMirrorKit is to generate a ready-to-use Claude Code project folder that enables recreating a functionally equivalent application. Currently there is no synthesis step that assembles harvest output into a CLAUDE.md file, agent definitions, and stack conventions. The "mirror" in RepoMirrorKit doesn't yet exist.

## Goal

Implement a Stage G that synthesizes all harvest artifacts into a Claude Code project folder: a CLAUDE.md file with cross-cutting rules, stack conventions, team roster, and workflow references; agent files tailored to the analyzed project; and stack convention files derived from detected technologies and patterns.

## Scope

### In Scope
- New pipeline stage: Stage G ("Generate project folder")
- Implement `src/repo_mirror_kit/harvester/generator/` package:
  - `claude_md.py` — Generates CLAUDE.md from surfaces, detected stack, and project metadata
  - `agents.py` — Generates agent files based on project characteristics (which personas are relevant)
  - `stacks.py` — Generates stack convention files from detected frameworks and patterns
  - `assembler.py` — Orchestrates generation, creates output directory structure
- CLAUDE.md generation includes:
  - Project name and description (from README or repo metadata)
  - Tech stack quick reference (from detected frameworks/languages)
  - Cross-cutting safety and quality rules (standard set, customized to detected patterns)
  - Team roster (subset of personas relevant to the project)
  - Workflow references pointing to generated beans, surface map, traceability
- Agent file generation:
  - Developer agent with project-specific context (detected stack, key files, patterns)
  - Architect agent with system overview (components, APIs, data flow)
  - Tech-QA agent with test strategy (detected test frameworks, coverage gates)
  - Additional agents based on project complexity (security if auth detected, devops if CI/CD detected)
- Stack convention generation:
  - Language conventions based on detected primary language
  - Framework conventions based on detected frameworks
  - Tooling conventions (linter, formatter, test runner, package manager)
- Output directory structure: `output/project-folder/.claude/`, `output/project-folder/CLAUDE.md`
- Wire into pipeline after Stage F
- Unit tests

### Out of Scope
- Generating application source code
- Interactive customization wizard
- Multi-project monorepo splitting
- Comparing generated folder against original project
- Publishing or deploying the generated folder

## Acceptance Criteria

- [x] Stage G exists in pipeline after Stage F
- [x] `generator/` package exists with claude_md.py, agents.py, stacks.py, assembler.py
- [x] Generated CLAUDE.md includes project name, tech stack table, and cross-cutting rules
- [x] Generated CLAUDE.md includes team roster with agent file references
- [x] Generated CLAUDE.md includes workflow references to beans and reports
- [x] Stack conventions file generated matching detected primary language/framework
- [x] Developer agent file generated with project-specific paths and patterns
- [x] At least 3 agent files generated (developer, architect, tech-qa) for any project
- [x] Additional agents generated conditionally (security if auth surfaces exist, devops if build/deploy surfaces exist)
- [x] Output directory follows Claude Code project structure (.claude/agents/, CLAUDE.md at root)
- [x] Generated files are valid markdown with no broken references
- [x] Pipeline completes Stage G and reports generated file count
- [x] Unit tests cover CLAUDE.md generation, agent generation, stack generation
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Design output directory structure and CLAUDE.md template | Architect | — | Done |
| 2 | Implement claude_md.py generator | Developer | 1 | Done |
| 3 | Implement stacks.py generator | Developer | 1 | Done |
| 4 | Implement agents.py generator | Developer | 1, 3 | Done |
| 5 | Implement assembler.py orchestrator | Developer | 2, 3, 4 | Done |
| 6 | Add Stage G to pipeline | Developer | 5 | Done |
| 7 | Write unit tests | Tech-QA | 2, 3, 4, 5 | Done |
| 8 | Run lint, type-check, and test suite | Tech-QA | 6, 7 | Done |

## Notes

- Depends on all analyzer beans (BEAN-019 through BEAN-036) for complete surface data.
- This is the capstone feature — it's what makes RepoMirrorKit a "mirror kit" rather than just an analyzer.
- The generated CLAUDE.md should follow the same structure as this project's own CLAUDE.md (which serves as a proven template).
- LLM enrichment data (behavioral descriptions, Given/When/Then criteria) should be woven into agent context so agents understand not just structure but behavior.
- Consider making the generated folder self-documenting: include a README explaining what was generated and how to use it with Claude Code.
- Stage G should be skippable (some users may only want the analysis artifacts, not the generated project folder).

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Design output directory structure and CLAUDE.md template | Architect | < 1m | 2,747,274 | 1,223 | $7.95 |
| 2 | Implement claude_md.py generator | Developer | < 1m | 17,015,110 | 20,059 | $36.34 |
| 3 | Implement stacks.py generator | Developer | < 1m | 17,162,899 | 20,060 | $36.56 |
| 4 | Implement agents.py generator | Developer | < 1m | 17,310,688 | 20,061 | $36.79 |
| 5 | Implement assembler.py orchestrator | Developer | < 1m | 17,458,477 | 20,062 | $37.01 |
| 6 | Add Stage G to pipeline | Developer | < 1m | 17,606,266 | 20,063 | $37.24 |
| 7 | Write unit tests | Tech-QA | < 1m | 17,754,055 | 20,064 | $37.46 |
| 8 | Run lint, type-check, and test suite | Tech-QA | < 1m | 17,901,844 | 20,065 | $37.69 |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 8 |
| **Total Duration** | 4m |
| **Total Tokens In** | 124,956,613 |
| **Total Tokens Out** | 141,657 |
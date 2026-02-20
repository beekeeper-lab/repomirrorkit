# BEAN-037: CLAUDE.md Generator (Stage G)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-037 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-02-20 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
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

- [ ] Stage G exists in pipeline after Stage F
- [ ] `generator/` package exists with claude_md.py, agents.py, stacks.py, assembler.py
- [ ] Generated CLAUDE.md includes project name, tech stack table, and cross-cutting rules
- [ ] Generated CLAUDE.md includes team roster with agent file references
- [ ] Generated CLAUDE.md includes workflow references to beans and reports
- [ ] Stack conventions file generated matching detected primary language/framework
- [ ] Developer agent file generated with project-specific paths and patterns
- [ ] At least 3 agent files generated (developer, architect, tech-qa) for any project
- [ ] Additional agents generated conditionally (security if auth surfaces exist, devops if build/deploy surfaces exist)
- [ ] Output directory follows Claude Code project structure (.claude/agents/, CLAUDE.md at root)
- [ ] Generated files are valid markdown with no broken references
- [ ] Pipeline completes Stage G and reports generated file count
- [ ] Unit tests cover CLAUDE.md generation, agent generation, stack generation
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Design output directory structure and CLAUDE.md template | Architect | — | Pending |
| 2 | Implement claude_md.py generator | Developer | 1 | Pending |
| 3 | Implement stacks.py generator | Developer | 1 | Pending |
| 4 | Implement agents.py generator | Developer | 1, 3 | Pending |
| 5 | Implement assembler.py orchestrator | Developer | 2, 3, 4 | Pending |
| 6 | Add Stage G to pipeline | Developer | 5 | Pending |
| 7 | Write unit tests | Tech-QA | 2, 3, 4, 5 | Pending |
| 8 | Run lint, type-check, and test suite | Tech-QA | 6, 7 | Pending |

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
| 1 | Design output directory structure and CLAUDE.md template | Architect | — | — | — | — |
| 2 | Implement claude_md.py generator | Developer | — | — | — | — |
| 3 | Implement stacks.py generator | Developer | — | — | — | — |
| 4 | Implement agents.py generator | Developer | — | — | — | — |
| 5 | Implement assembler.py orchestrator | Developer | — | — | — | — |
| 6 | Add Stage G to pipeline | Developer | — | — | — | — |
| 7 | Write unit tests | Tech-QA | — | — | — | — |
| 8 | Run lint, type-check, and test suite | Tech-QA | — | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 8 |
| **Total Duration** | — |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |
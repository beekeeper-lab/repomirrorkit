# BEAN-003: Enforce Mandatory Tech QA in Long-Run Skill

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-003 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | Process |

## Problem Statement

The `/long-run` skill allows the Team Lead to skip any role in the wave (BA, Architect, Developer, Tech-QA) when it judges the role isn't needed. In practice, this means the Team Lead routinely skips Tech QA on "simple" beans and self-verifies the Developer's work. This is self-review with no independent validation — the same agent that wrote the code is confirming it works. Even a one-line change benefits from Tech QA confirming the test actually tests what it claims, the full suite passes, and acceptance criteria are genuinely met.

## Goal

Update the `/long-run` SKILL.md so that Tech QA is mandatory for all App and Infra category beans in both sequential and parallel execution modes. Only Process-only beans that modify no code (documentation updates, workflow changes) may skip Tech QA. BA and Architect remain skippable when not needed. After this change, no code bean can reach `Done` without independent Tech QA verification.

## Scope

### In Scope
- Update Phase 3, Step 10 (Decomposition) skip rule to enforce mandatory Tech QA for App/Infra beans
- Update Phase 4, Step 13 (Wave Execution) skip rule to reinforce mandatory Tech QA for App/Infra beans
- Update Parallel Mode worker spawn prompt (Parallel Phase 3, Step 8) to include the same mandatory Tech QA instruction
- Ensure skip reasons for BA/Architect are documented in the bean's Notes section

### Out of Scope
- Changing the wave order (BA, Architect, Developer, Tech-QA stays the same)
- Modifying any other skills or agents
- Adding enforcement mechanisms beyond the skill text (e.g., no automated gate or hook changes)
- Changing how Process-only beans are handled (Tech QA remains optional for pure docs/workflow beans)

## Acceptance Criteria

- [ ] Step 10 (Decomposition) explicitly states Tech QA is mandatory for App and Infra beans and may only be skipped for Process-only beans that modify no code
- [ ] Step 10 states BA and Architect may be skipped when not needed, with skip reasons documented in Notes
- [ ] Step 13 (Wave Execution) reinforces that Tech QA must never be skipped for App or Infra beans and explains why (independent verification of acceptance criteria, tests, lint)
- [ ] Step 13 states only BA and Architect may be skipped, with skip reasons in Notes
- [ ] Parallel mode worker spawn prompt includes the mandatory Tech QA rule (same policy as sequential)
- [ ] No other sections of SKILL.md are changed beyond the three targeted areas
- [ ] All changes are consistent — same policy stated in decomposition, execution, and parallel mode

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

> Tasks are populated by the Team Lead during decomposition.
> Task files go in `tasks/` subdirectory.

## Notes

- Target file: `.claude/skills/long-run/SKILL.md`
- Three edit locations: Step 10 (line ~70-71), Step 13 (line ~83-84), Parallel worker prompt (line ~179)
- This is a Process bean that modifies no application code — only a skill definition file

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

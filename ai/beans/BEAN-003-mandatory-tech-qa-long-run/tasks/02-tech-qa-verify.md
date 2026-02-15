# Task 02: Verify mandatory Tech QA policy edits

| Field | Value |
|-------|-------|
| **Owner** | Tech-QA |
| **Status** | Done |
| **Depends On** | Task 01 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |

## Goal

Independently verify that all 7 acceptance criteria from BEAN-003 are met by reading the updated SKILL.md.

## Inputs

- `.claude/skills/long-run/SKILL.md` (after Developer edits)
- BEAN-003 `bean.md` (acceptance criteria)

## Verification Checklist

- [ ] Step 10 explicitly states Tech QA is mandatory for App and Infra beans
- [ ] Step 10 states Tech QA may only be skipped for Process-only beans that modify no code
- [ ] Step 10 states BA and Architect may be skipped when not needed, with skip reasons documented in Notes
- [ ] Step 13 reinforces that Tech QA must never be skipped for App or Infra beans
- [ ] Step 13 explains why (independent verification of acceptance criteria, tests, lint)
- [ ] Step 13 states only BA and Architect may be skipped, with skip reasons in Notes
- [ ] Parallel mode worker spawn prompt includes the mandatory Tech QA rule
- [ ] No other sections of SKILL.md were changed beyond the three targeted areas
- [ ] All three locations state a consistent policy (no contradictions)

## Definition of Done

All 9 checklist items pass. Any failures are reported with specific line references.

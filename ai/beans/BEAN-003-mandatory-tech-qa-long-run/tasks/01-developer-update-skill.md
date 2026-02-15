# Task 01: Update /long-run SKILL.md with mandatory Tech QA policy

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Status** | Done |
| **Depends On** | — |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |

## Goal

Edit three sections of `.claude/skills/long-run/SKILL.md` to enforce mandatory Tech QA for App and Infra beans.

## Inputs

- `.claude/skills/long-run/SKILL.md` (current skill definition)
- BEAN-003 `bean.md` (acceptance criteria and scope)

## Work

1. **Step 10 (Decomposition):** Replace the permissive skip rule with:
   - Tech QA is mandatory for all App and Infra category beans. Only skip Tech QA for Process-only beans that modify no code.
   - BA and Architect may still be skipped when not needed. Document skip reasons in Notes.

2. **Step 13 (Wave Execution):** Replace the generic skip guidance with:
   - Tech QA must never be skipped for App or Infra beans — it provides independent verification.
   - Only BA and Architect may be skipped. Skip reasons must be documented in Notes.

3. **Parallel worker spawn prompt (Step 8):** Add the mandatory Tech QA rule to the worker instructions.

## Acceptance Criteria

- [ ] Step 10 explicitly states Tech QA mandatory for App/Infra, skippable only for Process no-code beans
- [ ] Step 10 states BA/Architect skippable with skip reasons in Notes
- [ ] Step 13 reinforces Tech QA mandatory for App/Infra with rationale
- [ ] Step 13 states only BA/Architect may be skipped, with skip reasons in Notes
- [ ] Parallel mode prompt includes mandatory Tech QA rule
- [ ] No other sections changed
- [ ] All three locations state the same consistent policy

## Definition of Done

All edits made to SKILL.md. No other files modified. The three sections are internally consistent.

# Task Seeding Plan

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| **Date**      | [YYYY-MM-DD]                   |
| **Owner**     | [Team Lead name or persona]    |
| **Objective** | [High-level goal this plan decomposes] |
| **Related**   | [Links to epic, ADR, or prior plan] |
| **Status**    | Draft / Reviewed / Approved    |

*Break a major objective into waves of tasks with clear ownership and dependencies. Each wave should be completable before the next begins.*

## Wave Overview

| Wave | Task ID | Task Title | Owner (Persona) | Depends On | Est. Effort |
|------|---------|------------|------------------|------------|-------------|
| 1    | [T-001] | [Title]    | [persona]        | --         | [S/M/L]     |
| 1    | [T-002] | [Title]    | [persona]        | --         | [S/M/L]     |
| 2    | [T-003] | [Title]    | [persona]        | T-001      | [S/M/L]     |
| 2    | [T-004] | [Title]    | [persona]        | T-001, T-002 | [S/M/L]  |
| 3    | [T-005] | [Title]    | [persona]        | T-003, T-004 | [S/M/L]  |

*Add rows as needed. Keep task IDs consistent with the task-spec documents.*

## Dependency Graph

*Text-based representation of task dependencies. Use indentation or arrows to show flow.*

```
T-001 ──┐
        ├──> T-003 ──┐
T-002 ──┤            ├──> T-005
        └──> T-004 ──┘
```

*Redraw for your actual tasks. The goal is to make the parallel and serial paths visible at a glance.*

## Critical Path

*Identify the longest chain of dependent tasks -- this determines minimum total duration.*

1. [T-001] -> [T-003] -> [T-005]

*If the critical path is too long, look for ways to split tasks or parallelize work.*

## Risk Flags

*Note anything that could derail the plan.*

| Risk | Affected Tasks | Likelihood | Impact | Mitigation |
|------|---------------|------------|--------|------------|
| [Risk description] | [T-00X, T-00Y] | High / Medium / Low | High / Medium / Low | [Action or contingency] |

## Notes

[Any additional context, constraints, or assumptions that shaped this plan.]

## Definition of Done

- [ ] Every task has a unique ID, clear owner, and defined dependencies
- [ ] Waves are sequenced so no task starts before its dependencies complete
- [ ] Critical path identified and reviewed for feasibility
- [ ] Risk flags documented with mitigations where possible
- [ ] Plan reviewed and approved by stakeholders

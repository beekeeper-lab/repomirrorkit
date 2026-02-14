# Integration Plan

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | [YYYY-MM-DD]                   |
| Owner         | [integration lead]             |
| Related links | [issue/PR/ADR URLs]            |
| Status        | Draft / Reviewed / Approved    |

## Integration Scope

*Identify which branches, features, or components are being integrated and the target branch.*

- **Target branch:** [e.g., main, release/1.2]
- **Integration window:** [start date] to [end date]
- **Branches / features in scope:**
  - [branch or feature name 1]
  - [branch or feature name 2]
  - [branch or feature name 3]

## Merge Sequence

*Define the order in which branches will be merged. Order matters -- merge foundational changes first.*

| Order | Branch / Feature     | Owner           | Depends On       | Status               |
|-------|----------------------|-----------------|------------------|-----------------------|
| 1     | [branch name]        | [person]        | None             | Pending / Merged      |
| 2     | [branch name]        | [person]        | [order 1]        | Pending / Merged      |
| 3     | [branch name]        | [person]        | [order 1, 2]     | Pending / Merged      |

## Dependency Graph

*Describe relationships between branches in text form. Use indentation to show dependencies.*

```
[branch A] (no dependencies)
  +-- [branch B] (depends on A)
  +-- [branch C] (depends on A)
        +-- [branch D] (depends on A and C)
```

## Critical Path

*Identify the sequence of merges that determines the minimum integration timeline.*

1. [branch name] -- estimated merge time: [duration]
2. [branch name] -- estimated merge time: [duration]
3. [branch name] -- estimated merge time: [duration]

**Total estimated integration time:** [duration]

## Risk Assessment

*Identify what could go wrong during integration.*

| Risk                            | Likelihood | Impact | Mitigation                          |
|---------------------------------|------------|--------|-------------------------------------|
| Conflicting file changes        | H / M / L  | H / M / L | [how to reduce or handle]        |
| Shared infrastructure changes   | H / M / L  | H / M / L | [how to reduce or handle]        |
| Database migration conflicts    | H / M / L  | H / M / L | [how to reduce or handle]        |
| [additional risk]               | H / M / L  | H / M / L | [how to reduce or handle]        |

## Communication Plan

*Define who needs to know what and when.*

| Audience              | Channel          | When                        | Message                    |
|-----------------------|------------------|-----------------------------|----------------------------|
| [development team]    | [channel/tool]   | Before integration begins   | [what to communicate]      |
| [QA team]             | [channel/tool]   | After each merge            | [what to communicate]      |
| [stakeholders]        | [channel/tool]   | After integration complete  | [what to communicate]      |

## Verification Steps

*After each merge, verify that the integration is healthy.*

- [ ] Build completes without errors
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] No new linting or static analysis warnings
- [ ] Application starts and basic smoke test passes
- [ ] Affected features manually verified
- [ ] Performance not degraded (if applicable)

## Definition of Done

- [ ] All branches merged in defined sequence
- [ ] Every merge verified with the checklist above
- [ ] No unresolved conflicts remaining
- [ ] CI pipeline fully green on target branch
- [ ] Integration log updated with outcomes
- [ ] Stakeholders notified of completion

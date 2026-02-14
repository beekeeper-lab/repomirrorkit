# Merge Checklist

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | [YYYY-MM-DD]                   |
| Owner         | [merge captain]                |
| Related links | [issue/PR/ADR URLs]            |
| Status        | Draft / Reviewed / Approved    |

## Merge Details

- **Source branch:** [branch being merged]
- **Target branch:** [branch receiving the merge]
- **Merge performed by:** [person]
- **Related integration plan:** [link or document name]

## Pre-Merge

*Confirm these conditions before starting the merge.*

- [ ] Source branch is up to date with the target branch (rebased or merged from target)
- [ ] CI pipeline passes on the source branch
- [ ] Code review approved with no outstanding change requests
- [ ] No known blockers or unresolved dependencies
- [ ] Feature flag configuration verified (if applicable)
- [ ] Database migrations reviewed and compatible with current schema
- [ ] Branch owner confirms the branch is ready to merge

## During Merge

*Follow these steps while performing the merge.*

- [ ] Conflicts identified and listed below
- [ ] Each conflict resolution documented with rationale
- [ ] Both sides' intent preserved in conflict resolution (no silent overwrites)
- [ ] No files accidentally deleted or reverted during resolution

### Conflict Resolution Log

| File Path               | Conflict Summary              | Resolution Taken            | Verified By    |
|-------------------------|-------------------------------|-----------------------------|----------------|
| [file path]             | [what conflicted]             | [how it was resolved]       | [person]       |
| [file path]             | [what conflicted]             | [how it was resolved]       | [person]       |

## Post-Merge

*Verify the merged result is healthy before moving on.*

- [ ] Build completes without errors on the target branch
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No regressions in existing functionality
- [ ] Cross-component tests pass (if applicable)
- [ ] Application starts correctly and smoke test passes
- [ ] No new warnings from linting or static analysis

## Documentation

*Ensure the merge is properly recorded.*

- [ ] Conflict resolutions documented in the log above
- [ ] Merge noted in the integration log or tracking tool
- [ ] Any follow-up tasks created for post-merge cleanup
- [ ] Branch owner notified of successful merge

## Definition of Done

- [ ] All pre-merge checks passed
- [ ] Merge completed with all conflicts resolved and documented
- [ ] All post-merge verifications passed
- [ ] Documentation updated

# Conflict Resolution Notes

## Metadata

| Field         | Value                                    |
|---------------|------------------------------------------|
| Date          | [YYYY-MM-DD]                             |
| Owner         | [Merge Captain name]                     |
| Related Links | [PR URLs, integration plan, merge checklist] |
| Status        | Draft / Reviewed / Approved              |

## Integration Context

*Describe the merge operation that produced these conflicts.*

- **Source branch:** [branch being merged]
- **Target branch:** [branch receiving the merge]
- **Integration type:** [Feature merge / Release integration / Hotfix / Rebase]
- **Merge initiated:** [YYYY-MM-DD HH:MM]
- **Related integration plan:** [link or document name]
- **Personas involved:** [Which personas authored the conflicting changes]

## Conflicts Summary

*List every conflict encountered during the merge. Use this table for quick reference; detailed resolution follows below.*

| File                        | Conflict Type              | Resolution Approach            |
|-----------------------------|----------------------------|--------------------------------|
| [path/to/file.ext]         | Concurrent edit / Delete vs. edit / Rename vs. edit | Ours / Theirs / Manual merge / Rewrite |
| [path/to/file.ext]         | [Conflict type]            | [Approach]                     |
| [path/to/file.ext]         | [Conflict type]            | [Approach]                     |

## Detailed Resolutions

*For each conflict, document both sides' intent and the resolution rationale.*

### Conflict 1: [path/to/file.ext]

- **Source branch intent:** [What the source branch was trying to accomplish in this file]
- **Target branch intent:** [What the target branch had changed or expected in this file]
- **Conflict description:** [Specific lines or sections that conflicted]
- **Resolution chosen:** [Exactly what the merged result looks like and why]
- **Rationale:** [Why this resolution preserves both sides' goals, or why one side was preferred]
- **Verification:** [How correctness was confirmed -- test run, manual review, diff inspection]

### Conflict 2: [path/to/file.ext]

- **Source branch intent:** [Source intent]
- **Target branch intent:** [Target intent]
- **Conflict description:** [What conflicted]
- **Resolution chosen:** [Merged result]
- **Rationale:** [Why this approach]
- **Verification:** [How verified]

### Conflict 3: [path/to/file.ext]

- **Source branch intent:** [Source intent]
- **Target branch intent:** [Target intent]
- **Conflict description:** [What conflicted]
- **Resolution chosen:** [Merged result]
- **Rationale:** [Why this approach]
- **Verification:** [How verified]

## Side Effects to Watch

*List anything that might break or behave unexpectedly as a result of the conflict resolutions.*

- [ ] [Describe a potential side effect and how to detect it]
- [ ] [Describe a potential side effect and how to detect it]
- [ ] [Describe a potential side effect and how to detect it]

*If no side effects are anticipated, write "None identified -- all resolutions verified to be isolated."*

## Lessons Learned

*Capture anything that would help avoid or simplify similar conflicts in the future.*

- [What caused these conflicts to arise -- timing, parallel work, missing coordination]
- [What could be done differently in branching strategy, communication, or task sequencing]
- [Any tooling or process improvements to recommend]

## Definition of Done

- [ ] Every conflict is listed in the summary table
- [ ] Each conflict has a detailed resolution with rationale
- [ ] Both sides' intent documented for every conflict
- [ ] All resolutions verified through testing or review
- [ ] Side effects identified and communicated to affected persona owners
- [ ] Lessons learned captured for retrospective
- [ ] Notes reviewed by at least one other team member

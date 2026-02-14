# Implementation Plan: [Feature / Story Title]

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | YYYY-MM-DD                     |
| Owner         | [Developer name]               |
| Related links | [Story / issue / design spec links] |
| Status        | Draft / Reviewed / Approved    |

*Step-by-step plan for implementing a story or feature. Write this before coding to surface unknowns early and align with reviewers.*

---

## Story Reference

- **Story/Issue:** [Link or ID]
- **Acceptance criteria summary:** [Brief restatement of what "done" looks like from the story]

---

## Approach Summary

*One to three sentences describing the overall implementation strategy.*

[Describe the high-level approach: what pattern or technique you will use, and why this approach was chosen over alternatives.]

---

## Implementation Steps

| Step | Description                                      | Estimated Effort |
|------|--------------------------------------------------|------------------|
| 1    | [e.g., Define data model and schema migration]   | [e.g., 2h]      |
| 2    | [e.g., Implement service layer logic]            | [e.g., 4h]      |
| 3    | [e.g., Add API endpoint and request validation]  | [e.g., 2h]      |
| 4    | [e.g., Write unit and integration tests]         | [e.g., 3h]      |
| 5    | [e.g., Update documentation and API contract]    | [e.g., 1h]      |

---

## Files to Modify or Create

*List the key files that will change so reviewers know the blast radius.*

| File Path                  | Change Type (New / Modify / Delete) | Purpose                     |
|----------------------------|-------------------------------------|-----------------------------|
| [src/models/resource.py]   | [New]                               | [Data model definition]     |
| [src/services/resource.py] | [New]                               | [Business logic]            |
| [src/api/routes.py]        | [Modify]                            | [Add new endpoint]          |
| [tests/test_resource.py]   | [New]                               | [Unit and integration tests]|

---

## Testing Approach

*How will you verify correctness?*

- **Unit tests:** [What logic will be unit tested and key edge cases]
- **Integration tests:** [What interactions will be tested end to end]
- **Manual verification:** [Any manual steps needed, e.g., "Verify response format via API client"]

---

## Risks and Unknowns

| Risk / Unknown                        | Impact  | Mitigation or Plan to Resolve         |
|---------------------------------------|---------|---------------------------------------|
| [e.g., Unclear requirements for edge case X] | [Medium] | [Clarify with BA before step 3]  |
| [e.g., Dependency on unreleased service Y]    | [High]   | [Use mock; integrate when available] |

---

## Dependencies

*Things that must be in place before or during implementation.*

- [ ] [e.g., Database migration from story ABC-123 must be merged first]
- [ ] [e.g., API contract reviewed and approved by architect]
- [ ] [e.g., Access credentials for staging environment]

---

## Definition of Done

- [ ] All implementation steps are complete
- [ ] Unit and integration tests pass
- [ ] Code reviewed and approved
- [ ] Acceptance criteria from the story are met
- [ ] Documentation updated if applicable
- [ ] No known regressions introduced

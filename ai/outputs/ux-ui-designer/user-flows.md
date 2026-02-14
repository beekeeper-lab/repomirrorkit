# User Flow

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | [YYYY-MM-DD]                   |
| Owner         | [flow author]                  |
| Related links | [issue/PR/ADR URLs]            |
| Status        | Draft / Reviewed / Approved    |

## Flow Overview

*Provide a brief summary of what this flow covers and why it matters.*

- **Flow name:** [descriptive name, e.g., "New user registration"]
- **Actor:** [user type or role, e.g., "Unauthenticated visitor"]
- **Goal:** [what the actor is trying to accomplish]

## Preconditions

*List anything that must be true before the flow begins.*

- [Precondition 1]
- [Precondition 2]

## Steps

*Number each step. Show the user action, the system response, and the resulting screen or state.*

| Step | User Action              | System Response               | Next Screen/State        |
|------|--------------------------|-------------------------------|--------------------------|
| 1    | [action description]     | [system feedback]             | [screen or state name]   |
| 2    | [action description]     | [system feedback]             | [screen or state name]   |
| 3    | [action description]     | [system feedback]             | [screen or state name]   |

## Decision Points

*Document any branches where the flow splits based on user choice or system logic.*

| Decision                    | Condition A path         | Condition B path         |
|-----------------------------|--------------------------|--------------------------|
| [decision description]      | [outcome and next step]  | [outcome and next step]  |

## Error Paths

*Describe what happens when something goes wrong at each critical step.*

| Trigger                     | Error Displayed          | Recovery Path            |
|-----------------------------|--------------------------|--------------------------|
| [what goes wrong]           | [message or indicator]   | [how the user recovers]  |

## End State

*Describe the successful completion state.*

- **Final screen/state:** [name or description]
- **Confirmation shown:** [what the user sees confirming success]
- **Side effects:** [emails sent, records created, etc.]

## Notes and Assumptions

- [Assumption about user behavior or system state]
- [Open question or dependency]

## Definition of Done

- [ ] All steps validated against current UI or prototype
- [ ] Decision points cover all known branches
- [ ] Error paths documented for each failure mode
- [ ] Flow reviewed by product owner or stakeholder
- [ ] Accessibility considerations noted where applicable

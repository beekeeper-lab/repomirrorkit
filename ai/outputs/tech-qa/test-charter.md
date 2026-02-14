# Exploratory Test Charter

## Metadata

| Field         | Value                              |
|---------------|------------------------------------|
| Date          | [YYYY-MM-DD]                       |
| Owner         | [Tester name]                      |
| Related Links | [Issue/PR/ADR references]          |
| Status        | Draft / Reviewed / Approved        |

---

## Charter Title

[Short, descriptive name for this exploration session]

## Area Under Test

*Identify the feature, component, or subsystem being explored.*

- **Component:** [Name or path]
- **Build / Version:** [Version or commit reference]
- **Environment:** [Environment used for this session]

## Mission / Goal

*What are you exploring for? What questions are you trying to answer?*

[e.g., "Explore the checkout flow under concurrent user sessions to find state management issues."]

## Time Box

- **Planned Duration:** [e.g., 60 minutes]
- **Actual Duration:** [Fill after session]

## Approach

*Describe techniques, heuristics, or personas you will use.*

- **Techniques:** [e.g., boundary analysis, error guessing, state transition]
- **Heuristics:** [e.g., SFDPOT -- Structure, Function, Data, Platform, Operations, Time]
- **User Personas:** [e.g., new user, power user, admin]
- **Focus Areas:** [e.g., error handling, edge cases, integration seams]

## Notes During Exploration

*Capture observations, surprises, and questions as you go.*

| Time  | Observation                                         |
|-------|-----------------------------------------------------|
| [HH:MM] | [What you did, what happened, what was surprising] |
| [HH:MM] | [What you did, what happened, what was surprising] |

## Issues Found

*Log any bugs or concerns discovered during the session.*

| # | Summary                | Severity       | Logged As       |
|---|------------------------|----------------|-----------------|
| 1 | [Brief description]    | [Crit/High/Med/Low] | [Bug tracker ID or TBD] |
| 2 | [Brief description]    | [Crit/High/Med/Low] | [Bug tracker ID or TBD] |

## Coverage Assessment

*How thoroughly did you cover the target area?*

- **Coverage Depth:** [Shallow / Moderate / Deep]
- **Areas Well Covered:** [List]
- **Areas Not Reached:** [List and reason]
- **Confidence Level:** [Low / Medium / High]

## Follow-Up Actions

- [ ] [File bug report for issue #X]
- [ ] [Write regression test for discovered behavior]
- [ ] [Schedule deeper session for uncovered area]
- [ ] [Discuss finding with developer / architect]

---

## Definition of Done

- [ ] Session completed within time box (or extension documented)
- [ ] All issues logged in bug tracker
- [ ] Charter notes reviewed and shared with team
- [ ] Follow-up actions assigned and tracked

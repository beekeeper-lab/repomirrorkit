# Traceability Matrix

## Metadata

| Field         | Value                              |
|---------------|------------------------------------|
| Date          | [YYYY-MM-DD]                       |
| Owner         | [QA Engineer name]                 |
| Related Links | [Issue/PR/ADR references]          |
| Status        | Draft / Reviewed / Approved        |

---

## Purpose

*Map stories and acceptance criteria to test cases and results to ensure complete, bidirectional traceability.*

## Release / Sprint Reference

- **Release / Sprint:** [Name or ID]
- **Last Updated:** [YYYY-MM-DD]

## Traceability Map

*Each row links a story to its acceptance criteria, the test cases that verify them, and the current result.*

| Story ID | Acceptance Criteria                  | Test Case ID(s) | Test Type              | Last Result       | Notes                  |
|----------|--------------------------------------|------------------|------------------------|-------------------|------------------------|
| [S-001]  | [AC description from the story]      | [TC-001, TC-002] | [Unit/Integration/E2E/Manual] | [Pass/Fail/Not Run] | [Any relevant notes] |
| [S-001]  | [Second AC for same story]           | [TC-003]         | [Unit/Integration/E2E/Manual] | [Pass/Fail/Not Run] | [Any relevant notes] |
| [S-002]  | [AC description from the story]      | [TC-004, TC-005] | [Unit/Integration/E2E/Manual] | [Pass/Fail/Not Run] | [Any relevant notes] |
| [S-003]  | [AC description from the story]      | [TC-006]         | [Unit/Integration/E2E/Manual] | [Pass/Fail/Not Run] | [Any relevant notes] |

## Coverage Summary

| Metric                             | Count |
|------------------------------------|-------|
| Total Stories                      | [N]   |
| Total Acceptance Criteria          | [N]   |
| AC with at least one test case     | [N]   |
| AC with no test case (gap)         | [N]   |
| **Traceability Coverage**          | [X%]  |

## Gaps and Actions

*List any acceptance criteria without test coverage and the plan to address them.*

| Story ID | Acceptance Criteria (Gap)            | Reason for Gap           | Action / Owner           |
|----------|--------------------------------------|--------------------------|--------------------------|
| [S-XXX]  | [AC that lacks test coverage]        | [e.g., Deferred, blocked]| [Plan to resolve / Name] |

---

## Definition of Done

- [ ] Every acceptance criterion has at least one mapped test case
- [ ] All test results are current (from latest test cycle)
- [ ] Gaps are documented with an action plan
- [ ] Matrix reviewed with Test Lead and Product Owner

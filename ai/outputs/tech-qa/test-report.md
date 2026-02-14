# Test Execution Report

## Metadata

| Field         | Value                              |
|---------------|------------------------------------|
| Date          | [YYYY-MM-DD]                       |
| Owner         | [Test Lead / QA Engineer name]     |
| Related Links | [Issue/PR/ADR references]          |
| Status        | Draft / Reviewed / Approved        |

---

## Test Cycle / Sprint Reference

- **Release / Sprint:** [Name or ID]
- **Test Period:** [YYYY-MM-DD] to [YYYY-MM-DD]
- **Build / Version:** [Version or commit reference]
- **Environment:** [Environment(s) used]

## Summary

*High-level counts of test execution results.*

| Metric              | Count |
|---------------------|-------|
| Total Test Cases    | [N]   |
| Passed              | [N]   |
| Failed              | [N]   |
| Blocked             | [N]   |
| Skipped             | [N]   |
| **Pass Rate**       | [X%]  |

## Defects Found

*List all defects discovered during this test cycle.*

| Defect ID | Title                  | Severity     | Status       | Assigned To |
|-----------|------------------------|--------------|--------------|-------------|
| [ID]      | [Brief description]    | [Crit/High/Med/Low] | [Open/Fixed/Deferred] | [Name] |
| [ID]      | [Brief description]    | [Crit/High/Med/Low] | [Open/Fixed/Deferred] | [Name] |

## Coverage Assessment

*Summarize what was tested and how thoroughly.*

| Area / Feature         | Planned Cases | Executed | Pass | Fail | Coverage |
|------------------------|---------------|----------|------|------|----------|
| [Feature A]            | [N]           | [N]      | [N]  | [N]  | [X%]     |
| [Feature B]            | [N]           | [N]      | [N]  | [N]  | [X%]     |

## Risks Identified During Testing

| Risk                                    | Impact   | Mitigation / Notes                     |
|-----------------------------------------|----------|----------------------------------------|
| [e.g., Flaky integration test suite]    | [H/M/L]  | [e.g., Investigated; env issue filed]  |
| [e.g., Untested edge case in module X]  | [H/M/L]  | [e.g., Added to next cycle backlog]    |

## Recommendation

*State the overall release recommendation based on test results.*

- [ ] **Release** -- All exit criteria met, no blocking defects.
- [ ] **Conditional Release** -- Release with known issues documented below.
- [ ] **Hold** -- Blocking defects remain; retest required after fixes.
- [ ] **Retest** -- Fixes applied; partial re-execution needed.

**Justification:** [Explain the rationale for the recommendation]

## Open Items

- [ ] [Unresolved item or action needed before release]
- [ ] [Unresolved item or action needed before release]

---

## Definition of Done

- [ ] All planned test cases executed or skipped with justification
- [ ] All defects logged and triaged
- [ ] Coverage assessment completed
- [ ] Recommendation reviewed with Tech Lead / Product Owner
- [ ] Report distributed to stakeholders

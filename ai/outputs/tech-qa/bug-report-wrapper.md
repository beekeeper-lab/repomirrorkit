# QA Bug Report Wrapper

## Metadata

| Field         | Value                              |
|---------------|------------------------------------|
| Date          | [YYYY-MM-DD]                       |
| Owner         | [QA Engineer name]                 |
| Related Links | [Issue/PR/ADR references]          |
| Status        | Draft / Reviewed / Approved        |

---

## Reference to Bug Report

*Link to the canonical bug report created from the BA bug report template.*

- **Bug Report Link:** [Link to BA bug report template instance]
- **Bug Tracker ID:** [ID in issue tracker]

---

## QA-Specific Additions

*The following fields supplement the BA canonical bug report with QA testing context.*

### Test Environment Details

| Attribute        | Value                              |
|------------------|------------------------------------|
| Environment      | [Dev / Staging / Production]       |
| OS / Platform    | [e.g., Linux, macOS, Windows]      |
| Browser / Client | [e.g., Chrome 120, API client]     |
| Build / Version  | [Version or commit reference]      |
| Configuration    | [Relevant config, feature flags]   |

### Reproduction Rate

- [ ] **Always** -- Reproduced on every attempt
- [ ] **Intermittent** -- Reproduced [X] out of [Y] attempts
- [ ] **Once** -- Could not reproduce after initial observation

**Reproduction Notes:** [Any patterns observed, timing, data conditions]

### Related Test Cases

*List test cases that exposed or are affected by this bug.*

| Test Case ID | Title                          | Result Before Bug | Notes              |
|--------------|--------------------------------|-------------------|--------------------|
| [TC-XXX]     | [Test case title]              | [Pass/Fail/N/A]   | [How it relates]   |
| [TC-XXX]     | [Test case title]              | [Pass/Fail/N/A]   | [How it relates]   |

### Regression Assessment

- **Is this a regression?** [ ] Yes / [ ] No / [ ] Unknown
- **Previously working in:** [Version or date when it last worked, if known]
- **Introduced in:** [Version or commit where it broke, if known]

### Severity Recommendation

*QA assessment based on testing impact and user exposure.*

- [ ] **Critical** -- System crash, data loss, complete feature failure
- [ ] **High** -- Major feature broken, no workaround
- [ ] **Medium** -- Feature impaired, workaround exists
- [ ] **Low** -- Minor inconvenience, cosmetic, edge case

**Justification:** [Why this severity level]

### Priority Recommendation

- [ ] **Urgent** -- Fix immediately, blocking release or other testing
- [ ] **High** -- Fix in current sprint/cycle
- [ ] **Medium** -- Fix before next release
- [ ] **Low** -- Fix when convenient

### Blocking Status

- **Blocking release?** [ ] Yes / [ ] No
- **Blocking other test cases?** [ ] Yes / [ ] No
- **Blocked tests:** [List test case IDs blocked by this bug, if any]

---

## Definition of Done

- [ ] Canonical bug report filed via BA template
- [ ] QA wrapper completed with all fields populated
- [ ] Severity and priority recommendations provided
- [ ] Related test cases linked
- [ ] Regression status assessed

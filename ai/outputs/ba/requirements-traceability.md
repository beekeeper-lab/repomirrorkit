# Requirements Traceability Matrix

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| **Date**      | [YYYY-MM-DD]                   |
| **Owner**     | [BA name or persona]           |
| **Project**   | [Project or epic name]         |
| **Related**   | [Links to epic brief, test plan, or release notes] |
| **Status**    | Draft / Reviewed / Approved    |

*Maintain one traceability matrix per project or epic. Update it as stories are written, tests are created, and releases ship. The goal is to answer: "Is every requirement covered by stories, tested, and released?"*

## Traceability Matrix

| Req ID | Requirement | Story ID | Test Case IDs | Release Version | Status |
|--------|-------------|----------|---------------|-----------------|--------|
| [REQ-001] | [Brief requirement description] | [US-000] | [TC-001, TC-002] | [v0.0.0 or "N/A"] | Defined / Implemented / Tested / Released |
| [REQ-002] | [Brief requirement description] | [US-000] | [TC-003] | [v0.0.0 or "N/A"] | Defined / Implemented / Tested / Released |
| [REQ-003] | [Brief requirement description] | [US-000, US-001] | [TC-004, TC-005] | [v0.0.0 or "N/A"] | Defined / Implemented / Tested / Released |

*Add rows as requirements are identified. A requirement may map to multiple stories and test cases.*

## Coverage Summary

| Status | Count | Percentage |
|--------|-------|------------|
| Defined | [n] | [n%] |
| Implemented | [n] | [n%] |
| Tested | [n] | [n%] |
| Released | [n] | [n%] |
| **Total** | [n] | 100% |

*Update this summary whenever the matrix changes. Gaps in coverage should be flagged immediately.*

## Gaps and Risks

*Requirements without stories, stories without tests, or tests without passing results.*

| Req ID | Gap Description | Action Needed | Owner |
|--------|----------------|---------------|-------|
| [REQ-00X] | [e.g., "No test cases written yet"] | [e.g., "QA to create test cases by Wave 3"] | [persona] |

## Definition of Done

- [ ] Every requirement has at least one linked story
- [ ] Every story has at least one linked test case
- [ ] Coverage summary is current and accurate
- [ ] Gaps identified with owners and resolution timeline
- [ ] Matrix reviewed at each release milestone

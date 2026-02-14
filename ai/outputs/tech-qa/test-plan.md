# Test Plan

## Metadata

| Field         | Value                              |
|---------------|------------------------------------|
| Date          | [YYYY-MM-DD]                       |
| Owner         | [Test Lead / QA Engineer name]     |
| Related Links | [Issue/PR/ADR references]          |
| Status        | Draft / Reviewed / Approved        |

---

## Feature / Release Reference

*Identify the feature, epic, or release this test plan covers.*

- **Feature / Release:** [Name or ID]
- **Version:** [X.Y.Z or sprint reference]
- **Description:** [Brief summary of what is being delivered]

## Scope

*Define what is in scope and what is explicitly excluded.*

**In Scope:**
- [ ] [Area or feature to be tested]
- [ ] [Area or feature to be tested]

**Out of Scope:**
- [Area explicitly not tested in this cycle and why]
- [Area explicitly not tested in this cycle and why]

## Test Strategy

*Describe the types of testing to be performed and relative emphasis.*

| Test Type     | Included | Approach / Notes                        |
|---------------|----------|-----------------------------------------|
| Unit          | Yes / No | [Owned by developers; QA reviews gaps]  |
| Integration   | Yes / No | [Describe integration points to cover]  |
| E2E           | Yes / No | [Describe critical user flows]          |
| Manual        | Yes / No | [Exploratory, usability, edge cases]    |
| Performance   | Yes / No | [Load targets, tools, thresholds]       |
| Security      | Yes / No | [Scans, pen testing, input validation]  |
| Accessibility | Yes / No | [Standards to verify]                   |

## Test Environments

*List environments required and their current readiness.*

| Environment | Purpose          | Status      | Notes                  |
|-------------|------------------|-------------|------------------------|
| [Dev]       | [Unit/debug]     | [Ready/TBD] | [Configuration notes] |
| [Staging]   | [Integration/E2E]| [Ready/TBD] | [Configuration notes] |

## Test Data Requirements

- [Describe data sets needed, synthetic data, anonymized production data, etc.]
- [Note any data setup or teardown procedures]

## Entry Criteria

*Testing can begin when all of the following are met.*

- [ ] Feature code is merged to the test branch
- [ ] Build passes CI with no blocking failures
- [ ] Test environment is provisioned and accessible
- [ ] Test data is loaded and verified
- [ ] [Additional entry condition]

## Exit Criteria

*Testing is considered complete when all of the following are met.*

- [ ] All planned test cases executed
- [ ] No open defects of severity Critical or High
- [ ] Code coverage meets threshold: [X%]
- [ ] Test report reviewed and signed off
- [ ] [Additional exit condition]

## Risks and Mitigations

| Risk                                    | Likelihood | Impact | Mitigation                          |
|-----------------------------------------|------------|--------|-------------------------------------|
| [e.g., Test environment instability]    | [H/M/L]   | [H/M/L]| [e.g., Provision backup environment]|
| [e.g., Incomplete requirements]         | [H/M/L]   | [H/M/L]| [e.g., Early exploratory sessions]  |

## Schedule

| Milestone              | Target Date  | Owner            |
|------------------------|--------------|------------------|
| Test plan approved     | [YYYY-MM-DD] | [Name]          |
| Test case authoring    | [YYYY-MM-DD] | [Name]          |
| Test execution start   | [YYYY-MM-DD] | [Name]          |
| Test execution end     | [YYYY-MM-DD] | [Name]          |
| Test report delivered  | [YYYY-MM-DD] | [Name]          |

## Responsibilities

| Role                | Person   | Responsibility                         |
|---------------------|----------|----------------------------------------|
| Test Lead           | [Name]   | Plan, coordinate, report               |
| QA Engineer(s)      | [Names]  | Author and execute test cases          |
| Developer(s)        | [Names]  | Fix defects, support environment setup |
| Product Owner       | [Name]   | Clarify requirements, accept results   |

---

## Definition of Done

- [ ] Test plan reviewed and approved by stakeholders
- [ ] All entry criteria met before execution begins
- [ ] All exit criteria met before sign-off
- [ ] Test report delivered and acknowledged

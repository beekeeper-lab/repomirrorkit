# Regression Checklist

## Metadata

| Field         | Value                              |
|---------------|------------------------------------|
| Date          | [YYYY-MM-DD]                       |
| Owner         | [QA Engineer name]                 |
| Related Links | [Issue/PR/ADR references]          |
| Status        | Draft / Reviewed / Approved        |

---

## Purpose

*Verify that existing functionality remains intact after changes. Run this checklist before each release or after significant changes.*

## Release / Build Reference

- **Release / Sprint:** [Name or ID]
- **Build / Version:** [Version or commit reference]
- **Change Summary:** [Brief description of what changed]

---

## Core Functionality

| Area / Component       | Critical Path to Test                    | Test Case Refs | Last Tested  | Result       | Notes        |
|------------------------|------------------------------------------|----------------|--------------|--------------|--------------|
| [e.g., User login]     | [Login with valid credentials]           | [TC-XXX]       | [YYYY-MM-DD] | [Pass/Fail]  | [Notes]      |
| [e.g., Data entry]     | [Create, read, update, delete records]   | [TC-XXX]       | [YYYY-MM-DD] | [Pass/Fail]  | [Notes]      |
| [e.g., Search]         | [Search with common and edge-case terms] | [TC-XXX]       | [YYYY-MM-DD] | [Pass/Fail]  | [Notes]      |

## Authentication and Authorization

| Area / Component       | Critical Path to Test                    | Test Case Refs | Last Tested  | Result       | Notes        |
|------------------------|------------------------------------------|----------------|--------------|--------------|--------------|
| [e.g., Role-based access] | [Admin vs. standard user permissions] | [TC-XXX]       | [YYYY-MM-DD] | [Pass/Fail]  | [Notes]      |
| [e.g., Session management]| [Timeout, logout, concurrent sessions]| [TC-XXX]       | [YYYY-MM-DD] | [Pass/Fail]  | [Notes]      |

## Data Integrity

| Area / Component       | Critical Path to Test                    | Test Case Refs | Last Tested  | Result       | Notes        |
|------------------------|------------------------------------------|----------------|--------------|--------------|--------------|
| [e.g., Data persistence]  | [Save and reload; verify consistency] | [TC-XXX]       | [YYYY-MM-DD] | [Pass/Fail]  | [Notes]      |
| [e.g., Validation rules]  | [Required fields, format checks]      | [TC-XXX]       | [YYYY-MM-DD] | [Pass/Fail]  | [Notes]      |

## Integrations

| Area / Component       | Critical Path to Test                    | Test Case Refs | Last Tested  | Result       | Notes        |
|------------------------|------------------------------------------|----------------|--------------|--------------|--------------|
| [e.g., External API]   | [Send request, verify response]          | [TC-XXX]       | [YYYY-MM-DD] | [Pass/Fail]  | [Notes]      |
| [e.g., Message queue]  | [Publish, consume, verify delivery]      | [TC-XXX]       | [YYYY-MM-DD] | [Pass/Fail]  | [Notes]      |

## Performance-Sensitive Paths

| Area / Component       | Critical Path to Test                    | Test Case Refs | Last Tested  | Result       | Notes        |
|------------------------|------------------------------------------|----------------|--------------|--------------|--------------|
| [e.g., Dashboard load]  | [Load with typical data volume]         | [TC-XXX]       | [YYYY-MM-DD] | [Pass/Fail]  | [Notes]      |
| [e.g., Bulk operations]  | [Process N records within threshold]   | [TC-XXX]       | [YYYY-MM-DD] | [Pass/Fail]  | [Notes]      |

---

## Summary

| Section                       | Total | Passed | Failed | Blocked |
|-------------------------------|-------|--------|--------|---------|
| Core Functionality            | [N]   | [N]    | [N]    | [N]     |
| Authentication/Authorization  | [N]   | [N]    | [N]    | [N]     |
| Data Integrity                | [N]   | [N]    | [N]    | [N]     |
| Integrations                  | [N]   | [N]    | [N]    | [N]     |
| Performance-Sensitive Paths   | [N]   | [N]    | [N]    | [N]     |

---

## Definition of Done

- [ ] All critical paths executed for every section
- [ ] No regression failures left unresolved or untracked
- [ ] Failed items logged as defects with severity assigned
- [ ] Checklist results shared with the team before release

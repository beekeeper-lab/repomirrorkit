# Mitigations Plan: [System or Feature Name]

## Metadata

| Field          | Value                                    |
|----------------|------------------------------------------|
| Date           | [YYYY-MM-DD]                             |
| Owner          | [Security Engineer name/role]            |
| Related Links  | [Threat model, ADR, issue tracker]       |
| Status         | Draft / Reviewed / Approved              |

---

## 1. Threat Model Reference

*Link this plan to its source threat model so mitigations stay traceable.*

| Field                   | Value                                       |
|-------------------------|---------------------------------------------|
| Threat Model Document   | [Link to threat-model-stride.md or equivalent] |
| Threat Model Version    | [1.0]                                       |
| System / Feature        | [Name of system being mitigated]            |
| Last Threat Model Review| [YYYY-MM-DD]                                |

---

## 2. Mitigations Tracker

*List every mitigation from the threat model. Each row must trace back to a specific threat.*

| Ref   | Threat Description                          | Mitigation Description                                  | Priority         | Owner         | Status                              | Verification Method                          | Target Date  | Notes              |
|-------|---------------------------------------------|----------------------------------------------------------|------------------|---------------|--------------------------------------|----------------------------------------------|-------------|---------------------|
| T-001 | [Forged authentication tokens]              | [Signed JWTs with short expiry; validate on every request] | [Critical]       | [Name/Team]   | [Planned/In Progress/Complete/Verified] | [Unit tests + penetration test]             | [YYYY-MM-DD] | [Any context]      |
| T-002 | [SQL injection via data access layer]       | [Parameterized queries; ORM enforced; no raw SQL]        | [Critical]       | [Name/Team]   | [Planned/In Progress/Complete/Verified] | [SAST scan + manual code review]            | [YYYY-MM-DD] | [Any context]      |
| T-003 | [Verbose error messages leak internals]     | [Generic errors in production; details in structured logs] | [High]          | [Name/Team]   | [Planned/In Progress/Complete/Verified] | [Manual test in staging]                    | [YYYY-MM-DD] | [Any context]      |
| T-004 | [Unauthenticated endpoint flooding]         | [Rate limiting at gateway; WAF rules]                    | [High]           | [Name/Team]   | [Planned/In Progress/Complete/Verified] | [Load test + monitoring review]             | [YYYY-MM-DD] | [Any context]      |
| T-005 | [IDOR on user data endpoints]               | [Authorization check on every resource access]           | [Critical]       | [Name/Team]   | [Planned/In Progress/Complete/Verified] | [Automated auth test suite]                 | [YYYY-MM-DD] | [Any context]      |
| [Add] | [Threat from model]                         | [Mitigation]                                             | [Critical/High/Medium/Low] | [Name/Team] | [Status]                           | [How to verify]                              | [YYYY-MM-DD] | [Notes]            |

---

## 3. Priority Definitions

*Use consistent priority levels across the plan.*

| Priority | Definition                                                       | Target Resolution Time |
|----------|------------------------------------------------------------------|------------------------|
| Critical | Exploitable vulnerability with direct path to data breach or RCE | [Within 1 sprint]      |
| High     | Significant risk that could be exploited with moderate effort    | [Within 2 sprints]     |
| Medium   | Risk with limited impact or lower likelihood                     | [Within 1 quarter]     |
| Low      | Minor risk; defense-in-depth measure                             | [Best effort / backlog]|

---

## 4. Verification Log

*Record when each mitigation was verified and by whom.*

| Ref   | Verification Date | Verified By    | Method Used                  | Result       | Notes              |
|-------|-------------------|----------------|------------------------------|--------------|---------------------|
| T-001 | [YYYY-MM-DD]      | [Name/Role]    | [Pen test / code review]     | [Pass/Fail]  | [Any context]       |
| T-002 | [YYYY-MM-DD]      | [Name/Role]    | [SAST scan]                  | [Pass/Fail]  | [Any context]       |
| [Add] |                   |                |                              |              |                     |

---

## 5. Progress Summary

*Update this section before each review meeting.*

| Priority | Total | Planned | In Progress | Complete | Verified |
|----------|-------|---------|-------------|----------|----------|
| Critical |       |         |             |          |          |
| High     |       |         |             |          |          |
| Medium   |       |         |             |          |          |
| Low      |       |         |             |          |          |

**Overall Mitigation Status:** [On Track / At Risk / Blocked]

**Blockers:** [List any blockers preventing mitigation progress]

---

## Definition of Done

- [ ] All threats from the threat model have corresponding mitigations
- [ ] Every mitigation has an owner, priority, and target date
- [ ] Verification method defined for each mitigation
- [ ] All Critical and High mitigations are Complete or Verified
- [ ] Verification log entries recorded for completed mitigations
- [ ] Progress summary current and reviewed by security lead

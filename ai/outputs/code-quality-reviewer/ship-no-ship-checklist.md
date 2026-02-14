# Ship/No-Ship Decision Checklist

## Metadata

| Field         | Value                              |
|---------------|------------------------------------|
| Date          | [YYYY-MM-DD]                       |
| Owner         | [Code Quality Reviewer name]       |
| Related Links | [Issue/PR/ADR references]          |
| Status        | Draft / Reviewed / Approved        |

---

**Project:** [Project Name]
**Version:** [X.Y.Z]
**Date:** YYYY-MM-DD
**Reviewer:** [Name/Role]
**Decision:** SHIP / NO-SHIP
**Blockers (if no-ship):** [List specific blocking items]

---

## How to Use This Checklist

Every item is marked with a severity level:

- **[BLOCKER]** -- Must pass. A single blocker failure means NO-SHIP.
- **[REQUIRED]** -- Must pass or have a documented exception approved by the
  Tech Lead. Two or more required failures without exceptions means NO-SHIP.
- **[RECOMMENDED]** -- Should pass. Failures are noted but do not block the
  release on their own.

Check the box when the item passes. If an item fails, note the reason in the
adjacent column. If an exception is granted, note the approver.

---

## 1. Code Quality

| Sev | Item | Pass | Notes |
|-----|------|------|-------|
| [BLOCKER] | No compiler errors or build failures. | [ ] | |
| [BLOCKER] | No known defects of severity Critical or High in the release scope. | [ ] | |
| [REQUIRED] | All new code has been peer-reviewed (no unreviewed commits). | [ ] | |
| [REQUIRED] | Static analysis (linter, type checker) passes with zero errors. | [ ] | |
| [REQUIRED] | No TODO/FIXME/HACK comments introduced without a linked tracking issue. | [ ] | |
| [RECOMMENDED] | Cyclomatic complexity of new functions stays below team threshold (default: 10). | [ ] | |
| [RECOMMENDED] | No new dependencies added without documented justification. | [ ] | |

---

## 2. Testing

| Sev | Item | Pass | Notes |
|-----|------|------|-------|
| [BLOCKER] | Unit test suite passes (100% green). | [ ] | |
| [BLOCKER] | Integration test suite passes (100% green). | [ ] | |
| [REQUIRED] | Code coverage for new code meets team threshold (default: 80%). | [ ] | |
| [REQUIRED] | No flaky tests in the release test run (if a test flakes, it was investigated). | [ ] | |
| [REQUIRED] | Edge cases and error paths have explicit test coverage. | [ ] | |
| [RECOMMENDED] | Performance/load tests executed if the change affects hot paths. | [ ] | |
| [RECOMMENDED] | Manual exploratory testing completed for user-facing changes. | [ ] | |

---

## 3. Security

| Sev | Item | Pass | Notes |
|-----|------|------|-------|
| [BLOCKER] | No known critical or high CVEs in dependencies (dependency scan clean). | [ ] | |
| [BLOCKER] | No secrets, credentials, or API keys committed to the repository. | [ ] | |
| [REQUIRED] | Threat model reviewed and updated if attack surface changed. | [ ] | |
| [REQUIRED] | Input validation present on all new external-facing endpoints. | [ ] | |
| [REQUIRED] | Authentication and authorization checks verified for new endpoints. | [ ] | |
| [RECOMMENDED] | SAST (static application security testing) scan completed with no new findings. | [ ] | |
| [RECOMMENDED] | Content Security Policy headers reviewed if frontend changes shipped. | [ ] | |

---

## 4. Performance

| Sev | Item | Pass | Notes |
|-----|------|------|-------|
| [REQUIRED] | No database queries without index coverage on production-scale data. | [ ] | |
| [REQUIRED] | No N+1 query patterns introduced. | [ ] | |
| [REQUIRED] | API response times within SLA targets on staging environment. | [ ] | |
| [RECOMMENDED] | Memory usage profiled -- no obvious leaks in long-running processes. | [ ] | |
| [RECOMMENDED] | Payload sizes reviewed -- no unnecessarily large responses. | [ ] | |
| [RECOMMENDED] | Caching strategy documented for any new high-frequency endpoints. | [ ] | |

---

## 5. Documentation

| Sev | Item | Pass | Notes |
|-----|------|------|-------|
| [REQUIRED] | CHANGELOG updated with user-facing description of changes. | [ ] | |
| [REQUIRED] | API documentation updated for new or modified endpoints. | [ ] | |
| [REQUIRED] | Architecture Decision Records created for significant design choices. | [ ] | |
| [RECOMMENDED] | README updated if setup steps, dependencies, or configuration changed. | [ ] | |
| [RECOMMENDED] | Runbook updated if operational procedures changed. | [ ] | |
| [RECOMMENDED] | Inline code comments explain non-obvious business logic. | [ ] | |

---

## 6. Operational Readiness

| Sev | Item | Pass | Notes |
|-----|------|------|-------|
| [BLOCKER] | Database migrations tested against production-scale data copy. | [ ] | |
| [BLOCKER] | Rollback procedure documented and verified. | [ ] | |
| [REQUIRED] | Monitoring and alerting covers new failure modes. | [ ] | |
| [REQUIRED] | Log output is structured, includes correlation IDs, and contains no PII. | [ ] | |
| [REQUIRED] | Feature flags configured correctly for gradual rollout (if applicable). | [ ] | |
| [RECOMMENDED] | Capacity planning reviewed -- expected load increase accounted for. | [ ] | |
| [RECOMMENDED] | On-call team briefed on the release and new failure modes. | [ ] | |

---

## Summary

| Category              | Blockers | Required | Recommended | Status  |
|-----------------------|----------|----------|-------------|---------|
| Code Quality          | /        | /        | /           | [P/F]   |
| Testing               | /        | /        | /           | [P/F]   |
| Security              | /        | /        | /           | [P/F]   |
| Performance           | /        | /        | /           | [P/F]   |
| Documentation         | /        | /        | /           | [P/F]   |
| Operational Readiness | /        | /        | /           | [P/F]   |

**Overall: SHIP / NO-SHIP**

**Sign-off:**

| Role                   | Name            | Decision       | Date       |
|------------------------|-----------------|----------------|------------|
| Code Quality Reviewer  | [Name]          | Ship / No-Ship | YYYY-MM-DD |
| Tech Lead              | [Name]          | Ship / No-Ship | YYYY-MM-DD |
| Security Engineer      | [Name]          | Ship / No-Ship | YYYY-MM-DD |

---

## Definition of Done

- [ ] Every BLOCKER item evaluated and marked Pass or Fail
- [ ] Every REQUIRED item evaluated; failures have documented exceptions or block the release
- [ ] Summary table tallied correctly
- [ ] Sign-off obtained from all required roles
- [ ] Decision recorded and communicated to the team

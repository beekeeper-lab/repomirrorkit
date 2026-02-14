# Rollback Runbook: [Project Name]

## Metadata

| Field          | Value                                    |
|----------------|------------------------------------------|
| Date           | [YYYY-MM-DD]                             |
| Owner          | [Release Manager or on-call engineer]    |
| Related Links  | [Release runbook, incident ticket, ADR]  |
| Status         | Draft / Reviewed / Approved              |

---

## 1. Rollback Decision Criteria

*Define the thresholds that trigger a rollback. If any criterion is met, proceed to the decision authority.*

| Criterion                  | Threshold                                    | Monitoring Source          |
|----------------------------|----------------------------------------------|----------------------------|
| Error rate (5xx)           | [> X% of requests for Y minutes]             | [Dashboard/tool name]      |
| Latency (p95 or p99)       | [> X ms for Y minutes]                       | [Dashboard/tool name]      |
| Critical smoke test failure | Any critical smoke test fails                | [Test suite or manual]     |
| Data integrity issue       | Any confirmed data corruption or loss         | [Alert/manual report]      |
| Security incident          | Active exploitation or critical vulnerability | [Security tooling/report]  |
| Dependent service failure  | [Downstream service degraded due to release]  | [Dashboard/tool name]      |

---

## 2. Decision Authority

*Identify who can authorize a rollback and escalation paths.*

| Scenario                          | Decision Maker              | Escalation Contact          |
|-----------------------------------|-----------------------------|-----------------------------|
| Within rollback window            | [Release Manager]           | [Engineering Lead]          |
| Outside rollback window           | [Engineering Lead]          | [VP Engineering / CTO]      |
| Data integrity or security issue  | [Security Engineer + Lead]  | [Incident Commander]        |

**Rollback Window:** [X hours after production deployment]

---

## 3. Rollback Steps

*Execute in order. Do not skip steps or improvise.*

1. Announce rollback decision in operations channel:
   "Rolling back [Project] from v[X.Y.Z] to v[X.Y.W]. Reason: [brief reason]."
2. Confirm the previous known-good version:
   - Version: [X.Y.W]
   - Artifact location: [registry path, S3 bucket, etc.]
3. Deploy previous version:
   - Command/pipeline: [specific command or pipeline trigger]
   - Expected duration: [N minutes]
4. Verify deployment completes without errors.
5. Run smoke tests against the rolled-back version.
6. Confirm monitoring metrics return to baseline.
7. Announce rollback completion in operations channel.

---

## 4. Database Rollback Considerations

*Database changes require special handling. Evaluate before rolling back.*

| Question                                           | Answer              |
|----------------------------------------------------|---------------------|
| Were database migrations applied in this release?  | [Yes / No]          |
| Are the migrations reversible?                     | [Yes / No / Partial]|
| Does the previous app version work with the new schema? | [Yes / No]     |
| Rollback migration command                         | [Command or N/A]    |

**If migrations are NOT reversible:**
- [ ] Escalate to [Database Admin / role] before proceeding
- [ ] Evaluate forward-fix as alternative to rollback
- [ ] Document data impact assessment

---

## 5. Feature Flag Rollback

*If the release enabled or modified feature flags, revert them.*

| Flag Name               | Release State | Rollback State | Owner         |
|--------------------------|---------------|----------------|---------------|
| [flag-name]              | [Enabled]     | [Disabled]     | [Name/Role]   |
| [flag-name]              | [Modified]    | [Previous val] | [Name/Role]   |

- [ ] All feature flags reverted to pre-release state
- [ ] Flag changes confirmed in flag management system

---

## 6. Communication Template

*Notify stakeholders promptly. Use the templates below.*

**Internal notification (operations channel):**
> Rollback initiated for [Project] v[X.Y.Z]. Reason: [reason]. Expected completion: [time]. Point of contact: [name].

**Stakeholder notification (email/chat):**
> Release v[X.Y.Z] of [Project] has been rolled back to v[X.Y.W] due to [brief reason]. Service is stable on the previous version. We are investigating and will provide an update by [time].

| Audience              | Channel            | Owner              |
|-----------------------|--------------------|--------------------|
| Engineering team      | [Operations chat]  | [Release Manager]  |
| Product stakeholders  | [Email / chat]     | [Product Manager]  |
| Affected customers    | [Status page]      | [Support Lead]     |

---

## 7. Post-Rollback Verification

*Confirm the system is healthy after rollback.*

- [ ] All smoke tests pass on rolled-back version
- [ ] Error rate returned to pre-release baseline
- [ ] Latency returned to pre-release baseline
- [ ] No data integrity issues detected
- [ ] Dependent services operating normally
- [ ] Customer-facing functionality verified

---

## 8. Post-Rollback Incident Creation

*Every rollback requires a follow-up incident report.*

| Field                  | Value                                       |
|------------------------|---------------------------------------------|
| Incident ticket        | [Link to newly created incident]            |
| Severity               | [P1 / P2 / P3]                             |
| Root cause owner       | [Name/Team]                                 |
| Timeline to RCA        | [24 hours / 48 hours / 1 week]             |
| Retrospective date     | [YYYY-MM-DD]                                |

- [ ] Incident ticket created within 1 hour of rollback
- [ ] Timeline of events documented
- [ ] Root cause investigation assigned
- [ ] Retrospective scheduled

---

## Definition of Done

- [ ] Rollback completed and verified with smoke tests
- [ ] All stakeholders notified
- [ ] Monitoring confirms system is healthy
- [ ] Incident ticket created and assigned
- [ ] Retrospective scheduled

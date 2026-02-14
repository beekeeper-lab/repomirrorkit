# Release Runbook: [Project Name] v[X.Y.Z]

## Metadata

| Field          | Value                                    |
|----------------|------------------------------------------|
| Date           | [YYYY-MM-DD]                             |
| Owner          | [Release Manager name/role]              |
| Related Links  | [Issue tracker, PR, ADR, or change request links] |
| Status         | Draft / Reviewed / Approved              |

---

**Release Date:** YYYY-MM-DD
**Release Manager:** [Name/Role]
**Approvals Required Before Deploy:** [List names/roles]
**Estimated Downtime:** [None / X minutes / maintenance window required]
**Rollback Deadline:** [Time after deploy by which rollback decision must be made]

---

## 1. Release Information

| Field                   | Value                                       |
|-------------------------|---------------------------------------------|
| Version                 | [X.Y.Z]                                     |
| Branch / Tag            | `release/vX.Y.Z` or `vX.Y.Z`               |
| Previous Production Ver | [X.Y.W]                                     |
| Changelog               | [Link to CHANGELOG or release notes]        |
| Ship/No-Ship Decision   | [Link to completed checklist]               |
| Threat Model Review     | [Link or "No security-relevant changes"]    |
| Database Migrations     | [Yes -- migration ID / No]                  |
| Feature Flags           | [List any flags being enabled/disabled]     |
| External Dependencies   | [Any third-party changes coordinated]       |

---

## 2. Pre-Release Checklist

*Complete every item. Do not proceed to build if any item is unchecked.*

- [ ] All code merged to release branch and branch is green on CI.
- [ ] Ship/no-ship checklist completed and approved.
- [ ] Database migration tested against a copy of production data.
- [ ] Environment variables and secrets confirmed in target environment.
- [ ] Feature flags set to intended state for this release.
- [ ] Monitoring dashboards reviewed -- baseline metrics captured.
- [ ] On-call engineer identified and confirmed available.
- [ ] Rollback procedure reviewed by at least one engineer besides the release
      manager.
- [ ] External stakeholders notified of release window (if applicable).
- [ ] Change request / change advisory board approval obtained (if required by
      org policy).

---

## 3. Build Steps

*Execute in order. Each step must succeed before proceeding.*

```
Step 1: Tag the release
  $ git tag -a vX.Y.Z -m "Release vX.Y.Z"
  $ git push origin vX.Y.Z

Step 2: Trigger CI/CD build
  - Pipeline: [pipeline name/URL]
  - Expected duration: [N minutes]
  - Artifact output: [location, e.g., container registry, S3 bucket]

Step 3: Verify build artifacts
  - Confirm artifact hash matches CI output.
  - Confirm artifact version label is vX.Y.Z.
  - Confirm container image scanned with no critical vulnerabilities.
```

**Build Artifact Verification:**

| Artifact              | Expected Hash / Version | Verified |
|-----------------------|------------------------|----------|
| Container image       | sha256:...             | [ ]      |
| Database migration    | migration_NNNN         | [ ]      |
| Static assets (if any)| [hash or version]      | [ ]      |

---

## 4. Deployment Steps

### 4.1 Staging Deployment

```
Step 1: Deploy to staging environment.
  - Command / pipeline: [specific command or pipeline trigger]
  - Expected duration: [N minutes]

Step 2: Run staging smoke tests (see Section 5).

Step 3: Hold for [N minutes] to observe error rates and latency.
```

- [ ] Staging deployment successful.
- [ ] Staging smoke tests passing.
- [ ] No anomalies in staging monitoring for [N] minutes.

### 4.2 Production Deployment

**Go/No-Go Decision:** Release Manager confirms all staging checks pass.

```
Step 1: Enable maintenance mode (if applicable).
  - Command: [specific command]

Step 2: Run database migrations (if applicable).
  - Command: [specific command]
  - Verify: [how to confirm migration succeeded]

Step 3: Deploy application.
  - Strategy: [rolling update / blue-green / canary]
  - Command / pipeline: [specific command or pipeline trigger]
  - Expected duration: [N minutes]

Step 4: Disable maintenance mode (if applicable).

Step 5: Run production smoke tests (see Section 5).
```

- [ ] Production deployment successful.
- [ ] Production smoke tests passing.
- [ ] Error rate within normal bounds for [N] minutes post-deploy.

---

## 5. Smoke Tests

*Execute immediately after each deployment. Failure on any critical test triggers the rollback procedure.*

| Test                                    | Type     | Expected Result          | Pass |
|-----------------------------------------|----------|--------------------------|------|
| Health check endpoint returns 200       | Critical | `GET /health` -> 200     | [ ]  |
| Login flow completes successfully       | Critical | User can authenticate     | [ ]  |
| Primary API endpoint returns valid data | Critical | `GET /api/v1/...` -> 200 | [ ]  |
| Background job processor is running     | Major    | Job queue draining        | [ ]  |
| Static assets load correctly            | Major    | No 404s on main page     | [ ]  |
| [Add application-specific tests]       |          |                          | [ ]  |

**Critical test failure = immediate rollback. Major test failure = release
manager judgment call within rollback deadline.**

---

## 6. Rollback Procedure

*If rollback is needed, execute these steps. Do not improvise.*

```
Step 1: Announce rollback in the operations channel.
  - Message: "Rolling back vX.Y.Z to vX.Y.W. Reason: [brief reason]."

Step 2: Revert application to previous version.
  - Command: [specific command to deploy vX.Y.W]
  - Expected duration: [N minutes]

Step 3: Revert database migrations (if applicable and reversible).
  - Command: [specific command]
  - WARNING: If migration is not reversible, STOP and escalate to [role].

Step 4: Verify rollback with smoke tests.

Step 5: Post-rollback incident report created within 24 hours.
```

- [ ] Rollback completed.
- [ ] Smoke tests passing on rolled-back version.
- [ ] Stakeholders notified of rollback.

---

## 7. Post-Release Tasks

*Complete within 24 hours of successful deployment.*

- [ ] Monitor error rates and latency for 24 hours post-deploy.
- [ ] Merge release branch back to main (if applicable).
- [ ] Update release tracking (Jira, GitHub release, internal tracker).
- [ ] Archive build artifacts with release tag.
- [ ] Send release announcement (see Communication Plan below).
- [ ] Schedule retrospective if release had significant issues.

---

## 8. Communication Plan

| Audience              | Channel           | Timing              | Message                          |
|-----------------------|-------------------|----------------------|----------------------------------|
| Engineering team      | Team chat channel | Before deploy starts | "Starting deploy of vX.Y.Z"     |
| Engineering team      | Team chat channel | After deploy         | "vX.Y.Z deployed successfully"   |
| Stakeholders          | Email / Slack     | After verification   | Release notes summary            |
| End users (if needed) | Status page / blog| After verification   | User-facing changelog            |
| On-call               | PagerDuty / chat  | Before deploy starts | "Release in progress, heads up"  |

---

## 9. Incident Contacts

| Role                  | Name              | Contact              |
|-----------------------|-------------------|----------------------|
| Release Manager       | [Name]            | [Phone/Slack handle] |
| On-Call Engineer      | [Name]            | [Phone/Slack handle] |
| Database Admin        | [Name]            | [Phone/Slack handle] |
| Engineering Lead      | [Name]            | [Phone/Slack handle] |

---

## Definition of Done

- [ ] All pre-release checklist items completed
- [ ] Build artifacts verified and hash-matched
- [ ] Staging deployment and smoke tests passed
- [ ] Go/no-go decision recorded
- [ ] Production deployment and smoke tests passed
- [ ] Post-release monitoring confirmed stable for 24 hours
- [ ] Communication plan executed
- [ ] Release tracking updated and artifacts archived

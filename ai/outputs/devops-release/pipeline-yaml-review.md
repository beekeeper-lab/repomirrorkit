# CI/CD Pipeline Review Checklist

## Metadata

| Field          | Value                                    |
|----------------|------------------------------------------|
| Date           | [YYYY-MM-DD]                             |
| Owner          | [Reviewer name/role]                     |
| Related Links  | [PR link, pipeline config path, ADR]     |
| Status         | Draft / Reviewed / Approved              |

---

## Pipeline Identification

*Record which pipeline is being reviewed and what changed.*

| Field               | Value                                      |
|---------------------|--------------------------------------------|
| Pipeline Name       | [Name of CI/CD pipeline]                   |
| Config File Path    | [e.g., .github/workflows/ci.yml]          |
| Branch/PR           | [Branch name or PR number]                 |
| Change Description  | [Brief summary of what changed and why]    |
| Previous Version    | [Link to last known-good config, if any]   |

---

## Build Stage

*Verify the build stage produces reliable, reproducible artifacts.*

- [ ] Dependencies are cached between runs
- [ ] Language/runtime versions are pinned explicitly
- [ ] Build output is reproducible (same input = same output)
- [ ] Build artifacts are tagged with commit SHA or version
- [ ] Build matrix covers all required target environments
- [ ] Build timeout is set to a reasonable value

---

## Test Stage

*Verify all test suites run and results are captured.*

- [ ] Unit tests are included and required to pass
- [ ] Integration tests are included (if applicable)
- [ ] Test timeouts are configured to prevent hanging jobs
- [ ] Test artifacts (reports, coverage) are captured and uploaded
- [ ] Test results gate the pipeline (failure blocks progression)
- [ ] Flaky test handling is documented (retry policy, quarantine)

---

## Security Stage

*Verify security scanning is enabled and blocking on findings.*

- [ ] Static application security testing (SAST) is enabled
- [ ] Software composition analysis (SCA) / dependency scanning is enabled
- [ ] Secrets scanning is enabled and runs on every commit
- [ ] Container image scanning is enabled (if applicable)
- [ ] Security scan failures block the pipeline at appropriate severity
- [ ] Scan results are reported to a central dashboard or tracker

---

## Deploy Stage

*Verify deployment targets, strategy, and safeguards.*

- [ ] Environment targeting is correct (dev/staging/prod)
- [ ] Deployment strategy is defined (rolling / blue-green / canary)
- [ ] Rollback path exists and is documented
- [ ] Manual approval gates are configured for production
- [ ] Deployment credentials use least-privilege service accounts
- [ ] Post-deploy health checks or smoke tests are included

---

## General Pipeline Hygiene

*Verify overall pipeline quality and security posture.*

- [ ] No hardcoded secrets, tokens, or credentials in pipeline config
- [ ] All third-party actions/images are pinned by SHA (not tag alone)
- [ ] Concurrency groups are set to prevent conflicting parallel runs
- [ ] Pipeline permissions follow least-privilege principle
- [ ] Notification/alerting is configured for pipeline failures
- [ ] Pipeline run duration is within acceptable limits
- [ ] Pipeline config is version-controlled and changes require review

---

## Findings

*Record any issues found during the review.*

| Finding                        | Severity        | Recommendation               | Resolved |
|--------------------------------|-----------------|------------------------------|----------|
| [Description of issue]         | [Critical/High/Medium/Low] | [What to fix]     | [ ]      |
| [Description of issue]         | [Critical/High/Medium/Low] | [What to fix]     | [ ]      |

---

## Definition of Done

- [ ] All checklist categories reviewed
- [ ] All Critical and High findings resolved
- [ ] Medium findings resolved or tracked with ticket
- [ ] Pipeline tested end-to-end on a non-production branch
- [ ] Review approved by pipeline owner and at least one other engineer

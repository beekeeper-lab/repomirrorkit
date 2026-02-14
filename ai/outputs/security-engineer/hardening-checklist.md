# Hardening Checklist: [System or Environment Name]

## Metadata

| Field          | Value                                    |
|----------------|------------------------------------------|
| Date           | [YYYY-MM-DD]                             |
| Owner          | [Security Engineer / DevOps Lead]        |
| Related Links  | [Environment matrix, threat model, ADR]  |
| Status         | Draft / Reviewed / Approved              |

---

## Scope

*Identify what is being hardened and the target environment.*

| Field                  | Value                                       |
|------------------------|---------------------------------------------|
| System / Service       | [Name of system or service]                 |
| Environment            | [Development / Staging / Production]        |
| Last Hardening Review  | [YYYY-MM-DD or "Initial"]                   |
| Reviewer               | [Name/Role]                                 |

---

## Network

*Verify network-level controls are in place.*

- [ ] TLS 1.2 or higher enforced on all external connections
- [ ] TLS 1.2 or higher enforced on all internal service-to-service connections
- [ ] Unnecessary ports are closed (only required ports open)
- [ ] Firewall rules reviewed and follow least-privilege
- [ ] Network segmentation isolates sensitive tiers (database, admin)
- [ ] DNS is secured (DNSSEC or equivalent, no zone transfer leaks)
- [ ] Load balancer / reverse proxy terminates TLS correctly

---

## Application

*Verify application-level security settings.*

- [ ] Security headers configured (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- [ ] Debug mode is disabled in all non-development environments
- [ ] Error messages are generic (no stack traces, internal paths, or versions)
- [ ] Directory listing is disabled on web servers
- [ ] Default accounts and sample pages are removed
- [ ] Application runs with a dedicated, least-privilege service account
- [ ] HTTP methods restricted to only those required per endpoint

---

## Authentication

*Verify authentication hardening measures.*

- [ ] Strong password policy enforced (minimum length, complexity)
- [ ] Account lockout or rate limiting after failed attempts
- [ ] Session timeouts configured (idle and absolute)
- [ ] Session tokens regenerated after authentication
- [ ] Multi-factor authentication (MFA) enabled for privileged accounts
- [ ] Default credentials changed or removed
- [ ] Password storage uses a strong, salted hashing algorithm

---

## Secrets Management

*Verify secrets are stored and handled securely.*

- [ ] No secrets in source code or configuration files
- [ ] No secrets in container images or build artifacts
- [ ] Secrets are stored in a dedicated secrets manager or vault
- [ ] Secrets are injected at runtime, not baked into deployments
- [ ] Rotation schedule is defined and followed (see secrets-rotation-plan.md)
- [ ] Access to secrets is restricted to authorized services and personnel
- [ ] Secret access is audited and logged

---

## Dependencies

*Verify third-party dependencies are managed securely.*

- [ ] No known critical or high CVEs in current dependencies
- [ ] Dependency lockfile is committed and used in builds
- [ ] Automated dependency scanning is enabled in CI/CD
- [ ] Unused dependencies are removed
- [ ] Container base images are from trusted sources and regularly updated
- [ ] Third-party actions/plugins are pinned by SHA or version

---

## Monitoring and Logging

*Verify security events are captured and actionable.*

- [ ] Security-relevant events are logged (auth failures, access denials, privilege changes)
- [ ] Logs do not contain secrets, passwords, or unmasked PII
- [ ] Log integrity is protected (append-only, tamper-evident, or shipped to central system)
- [ ] Alerting is configured for security anomalies (spike in auth failures, unusual access patterns)
- [ ] Audit trail is enabled for administrative actions
- [ ] Log retention meets compliance and incident response requirements

---

## Findings

*Record any gaps found during the hardening review.*

| Finding                        | Category       | Severity         | Remediation                       | Status   |
|--------------------------------|----------------|------------------|-----------------------------------|----------|
| [Description of gap]           | [Network/App/etc] | [Critical/High/Medium/Low] | [Steps to fix]          | [Open/Fixed] |
| [Description of gap]           | [Network/App/etc] | [Critical/High/Medium/Low] | [Steps to fix]          | [Open/Fixed] |

---

## Definition of Done

- [ ] All checklist categories reviewed for the target environment
- [ ] All Critical and High findings remediated
- [ ] Medium findings remediated or tracked with tickets
- [ ] Low findings documented and accepted with justification
- [ ] Checklist reviewed and signed off by security lead
- [ ] Next review date scheduled (recommend quarterly for production)

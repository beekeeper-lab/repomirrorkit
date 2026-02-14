# Security Test Checklist: [System or Feature Name]

## Metadata

| Field          | Value                                    |
|----------------|------------------------------------------|
| Date           | [YYYY-MM-DD]                             |
| Owner          | [Security Engineer / QA name]            |
| Related Links  | [Threat model, test plan, ADR]           |
| Status         | Draft / Reviewed / Approved              |

---

## Scope

*Define what is being tested and any exclusions.*

| Field                  | Value                                       |
|------------------------|---------------------------------------------|
| System / Feature       | [Name of system or feature under test]      |
| Test Environment       | [Staging URL or environment name]           |
| In Scope               | [Components, endpoints, user flows]         |
| Out of Scope           | [Anything explicitly excluded and why]      |

---

## Authentication

*Verify authentication mechanisms resist common attacks.*

- [ ] Brute force protection is in place (account lockout or rate limiting)
- [ ] Password policy enforced (minimum length, complexity requirements)
- [ ] Session tokens are generated with sufficient entropy
- [ ] Session tokens expire after a defined idle timeout
- [ ] Session tokens are invalidated on logout
- [ ] Multi-factor authentication (MFA) functions correctly
- [ ] Password reset flow does not reveal whether an account exists
- [ ] Authentication over plaintext (HTTP) is rejected or redirected

---

## Authorization

*Verify users can only access what they are permitted to access.*

- [ ] Insecure Direct Object Reference (IDOR) tested across user roles
- [ ] Horizontal access control: User A cannot access User B's resources
- [ ] Vertical privilege escalation: Regular user cannot reach admin functions
- [ ] Role changes take effect immediately (no stale permissions)
- [ ] API endpoints enforce authorization independently of the UI
- [ ] Default-deny policy: unauthenticated requests are rejected unless explicitly public

---

## Input Validation

*Verify the application rejects or sanitizes malicious input.*

- [ ] Reflected and stored Cross-Site Scripting (XSS) tested
- [ ] SQL injection tested on all database-backed inputs
- [ ] Command injection tested on inputs passed to system commands
- [ ] Path traversal tested on file access parameters
- [ ] XML External Entity (XXE) tested if XML parsing is used
- [ ] Server-Side Request Forgery (SSRF) tested on URL inputs
- [ ] Input length limits enforced on all fields
- [ ] Content-type validation enforced on file uploads

---

## API Security

*Verify API endpoints are hardened against abuse.*

- [ ] Rate limiting is enforced on all public endpoints
- [ ] Authentication is required on all non-public endpoints
- [ ] Error responses do not leak stack traces, internal paths, or versions
- [ ] API versioning is in place and deprecated versions are disabled
- [ ] Request/response payloads are validated against a schema
- [ ] CORS policy is restrictive and correct for the application
- [ ] HTTP methods are restricted to those actually needed per endpoint

---

## Infrastructure

*Verify the deployment environment meets security baselines.*

- [ ] TLS is enforced on all connections (no plaintext fallback)
- [ ] TLS version is 1.2 or higher; weak cipher suites are disabled
- [ ] Security headers are set (HSTS, Content-Security-Policy, X-Frame-Options, X-Content-Type-Options)
- [ ] CORS is configured to allow only trusted origins
- [ ] Secrets are not exposed in environment variables visible to logs or errors
- [ ] Unused ports and services are closed
- [ ] Server/framework version headers are removed or suppressed

---

## Data Protection

*Verify data is protected at rest, in transit, and in logs.*

- [ ] Sensitive data is encrypted at rest (database, file storage)
- [ ] Sensitive data is encrypted in transit (TLS end-to-end)
- [ ] PII is handled according to the data classification policy
- [ ] Logs do not contain passwords, tokens, PII, or secrets
- [ ] Backup data is encrypted and access-controlled
- [ ] Data retention and deletion policies are implemented

---

## Findings

*Record any issues discovered during testing.*

| Finding                        | Category       | Severity         | Reproduction Steps          | Status   |
|--------------------------------|----------------|------------------|-----------------------------|----------|
| [Description of finding]       | [Auth/Input/etc] | [Critical/High/Medium/Low] | [Brief steps to reproduce] | [Open/Fixed/Accepted] |
| [Description of finding]       | [Auth/Input/etc] | [Critical/High/Medium/Low] | [Brief steps to reproduce] | [Open/Fixed/Accepted] |

---

## Definition of Done

- [ ] All checklist categories tested
- [ ] All Critical and High findings fixed and retested
- [ ] Medium findings fixed or tracked with tickets
- [ ] Low findings documented and accepted with justification
- [ ] Test results reviewed by security lead
- [ ] Findings linked back to threat model mitigations where applicable

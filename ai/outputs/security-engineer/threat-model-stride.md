# Threat Model: [System or Feature Name]

## Metadata

| Field          | Value                                    |
|----------------|------------------------------------------|
| Date           | [YYYY-MM-DD]                             |
| Owner          | [Security Engineer name/role]            |
| Related Links  | [Architecture doc, ADR, issue tracker]   |
| Status         | Draft / Reviewed / Approved              |

**Version:** [1.0]
**Next Review Date:** [YYYY-MM-DD] *(no more than 6 months from approval)*

---

## 1. System Overview

*Describe the system or feature being modeled. Include a brief functional description and an architecture diagram reference if available.*

**Description:** [What does this system do in 2-3 sentences?]

**Architecture Diagram:** [Link or path to diagram, e.g., `docs/diagrams/system-arch.png`]

**Technology Stack:** [Languages, frameworks, databases, cloud services]

**Authentication Mechanism:** [OAuth2, API keys, mTLS, session cookies, etc.]

**Data Classification:** [Public | Internal | Confidential | Restricted]

---

## 2. Assets

*What are we protecting? List data, services, and capabilities that have value to an attacker or whose compromise would cause harm.*

| Asset                    | Classification | Storage Location       | Owner         |
|--------------------------|---------------|------------------------|---------------|
| User credentials         | Restricted    | Auth database          | [Team/Role]   |
| Session tokens           | Confidential  | In-memory / Redis      | [Team/Role]   |
| PII (names, emails)      | Confidential  | Primary database       | [Team/Role]   |
| Application source code  | Internal      | Git repository         | [Team/Role]   |
| API keys / secrets       | Restricted    | Secrets manager        | [Team/Role]   |
| [Add rows as needed]     |               |                        |               |

---

## 3. Trust Boundaries

*Where does trust change? Every point where data crosses from one trust level to another is a potential attack surface.*

| Boundary                          | From (Trust Level)    | To (Trust Level)      |
|-----------------------------------|-----------------------|-----------------------|
| Public internet to load balancer  | Untrusted             | DMZ                   |
| Load balancer to application tier | DMZ                   | Trusted (internal)    |
| Application tier to database      | Trusted (internal)    | Trusted (data layer)  |
| Application tier to third-party API | Trusted (internal) | External (vendor)     |
| Client browser to API             | Untrusted             | Trusted (internal)    |
| [Add rows as needed]              |                       |                       |

---

## 4. STRIDE Analysis

*For each trust boundary or major component, analyze threats across all six STRIDE categories. Not every category applies everywhere -- mark N/A where genuinely not applicable, but err on the side of inclusion.*

### 4.1 Spoofing (Identity)

*Can an attacker pretend to be someone or something they are not?*

| Threat                                          | Component Affected | Likelihood | Impact | Risk   |
|-------------------------------------------------|-------------------|------------|--------|--------|
| Attacker forges authentication tokens           | Auth service      | [H/M/L]   | [H/M/L]| [H/M/L]|
| Attacker impersonates a trusted internal service| Service mesh      | [H/M/L]   | [H/M/L]| [H/M/L]|
| [Add rows as needed]                            |                   |            |        |        |

### 4.2 Tampering (Integrity)

*Can an attacker modify data, code, or configuration they should not?*

| Threat                                          | Component Affected | Likelihood | Impact | Risk   |
|-------------------------------------------------|-------------------|------------|--------|--------|
| Request body modified in transit (no TLS)       | API gateway       | [H/M/L]   | [H/M/L]| [H/M/L]|
| Database records altered via SQL injection      | Data access layer | [H/M/L]   | [H/M/L]| [H/M/L]|
| [Add rows as needed]                            |                   |            |        |        |

### 4.3 Repudiation

*Can an attacker perform actions without them being traced?*

| Threat                                          | Component Affected | Likelihood | Impact | Risk   |
|-------------------------------------------------|-------------------|------------|--------|--------|
| User denies performing a destructive action     | Audit log service | [H/M/L]   | [H/M/L]| [H/M/L]|
| Admin actions not logged with identity           | Admin console     | [H/M/L]   | [H/M/L]| [H/M/L]|
| [Add rows as needed]                            |                   |            |        |        |

### 4.4 Information Disclosure (Confidentiality)

*Can an attacker access data they should not see?*

| Threat                                          | Component Affected | Likelihood | Impact | Risk   |
|-------------------------------------------------|-------------------|------------|--------|--------|
| Verbose error messages leak internal state      | API responses     | [H/M/L]   | [H/M/L]| [H/M/L]|
| Logs contain PII or secrets in plaintext        | Logging pipeline  | [H/M/L]   | [H/M/L]| [H/M/L]|
| [Add rows as needed]                            |                   |            |        |        |

### 4.5 Denial of Service (Availability)

*Can an attacker degrade or destroy service availability?*

| Threat                                          | Component Affected | Likelihood | Impact | Risk   |
|-------------------------------------------------|-------------------|------------|--------|--------|
| Unauthenticated endpoint flooded with requests  | API gateway       | [H/M/L]   | [H/M/L]| [H/M/L]|
| Large payload causes OOM in application         | Request handler   | [H/M/L]   | [H/M/L]| [H/M/L]|
| [Add rows as needed]                            |                   |            |        |        |

### 4.6 Elevation of Privilege

*Can an attacker gain capabilities beyond their authorized level?*

| Threat                                          | Component Affected | Likelihood | Impact | Risk   |
|-------------------------------------------------|-------------------|------------|--------|--------|
| IDOR allows user to access other users' data    | API endpoints     | [H/M/L]   | [H/M/L]| [H/M/L]|
| Missing role check on admin-only endpoint       | Authorization     | [H/M/L]   | [H/M/L]| [H/M/L]|
| [Add rows as needed]                            |                   |            |        |        |

---

## 5. Mitigations

*For every Medium or High risk identified above, define a mitigation. Low risks may be accepted with justification.*

| Threat (from above)                    | Mitigation                              | Status           | Owner       |
|----------------------------------------|-----------------------------------------|------------------|-------------|
| Forged authentication tokens           | Use signed JWTs with short expiry; validate signature on every request | [Planned/Done] | [Team/Role] |
| SQL injection                          | Parameterized queries only; no string concatenation in SQL | [Planned/Done] | [Team/Role] |
| Verbose error messages                 | Generic error responses in production; details only in structured logs | [Planned/Done] | [Team/Role] |
| Unauthenticated endpoint flooding      | Rate limiting at API gateway; WAF rules | [Planned/Done]   | [Team/Role] |
| [Add rows as needed]                   |                                         |                  |             |

---

## 6. Risk Rating Summary

| Risk Level | Count | Accepted | Mitigated | Remaining |
|------------|-------|----------|-----------|-----------|
| High       |       |          |           |           |
| Medium     |       |          |           |           |
| Low        |       |          |           |           |

**Overall Risk Posture:** [Acceptable | Needs Work | Unacceptable]

**Risk Acceptance:** Any accepted risks (not mitigated) must be documented
below with business justification and an approver:

| Accepted Risk               | Justification                    | Approved By | Date       |
|-----------------------------|----------------------------------|-------------|------------|
| [Risk description]          | [Why the team accepts this risk] | [Name/Role] | YYYY-MM-DD |

---

## 7. Review History

| Date       | Reviewer       | Changes Made                         |
|------------|----------------|--------------------------------------|
| YYYY-MM-DD | [Name/Role]    | Initial threat model created         |
| [Add rows] |                |                                      |

---

## Definition of Done

- [ ] System overview and architecture diagram referenced
- [ ] All assets identified and classified
- [ ] Trust boundaries mapped
- [ ] STRIDE analysis completed for all six categories
- [ ] Mitigations defined for all Medium and High risks
- [ ] Risk rating summary filled in with counts
- [ ] Accepted risks documented with business justification
- [ ] Threat model reviewed by at least one other security engineer
- [ ] Next review date set (within 6 months)

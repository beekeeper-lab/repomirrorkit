# Secure Design Review: [Feature or Component Name]

## Metadata

| Field          | Value                                    |
|----------------|------------------------------------------|
| Date           | [YYYY-MM-DD]                             |
| Owner          | [Security Engineer / Reviewer name]      |
| Related Links  | [Design doc, threat model, ADR, PR]      |
| Status         | Draft / Reviewed / Approved              |

---

## 1. Review Scope

*Identify what is being reviewed and the context for the review.*

| Field                       | Value                                       |
|-----------------------------|---------------------------------------------|
| Feature / Component         | [Name of feature or component]              |
| Reviewer(s)                 | [Name(s) and role(s)]                       |
| Design Document             | [Link to design doc or architecture spec]   |
| Review Requested By         | [Name/Team]                                 |
| Review Deadline              | [YYYY-MM-DD]                                |

---

## 2. Data Classification

*What data does this feature handle? Classification drives the required controls.*

| Data Element               | Classification                | Handling Requirements           |
|----------------------------|-------------------------------|---------------------------------|
| [e.g., User email address] | [Public/Internal/Confidential/Restricted] | [Encrypt at rest, mask in logs] |
| [e.g., Payment token]      | [Restricted]                  | [Never store, pass-through only]|
| [Add rows as needed]       |                               |                                 |

---

## 3. Authentication and Authorization Model

*Describe how users and services authenticate and how access is controlled.*

| Question                                          | Answer                                     |
|---------------------------------------------------|--------------------------------------------|
| How do users authenticate?                        | [OAuth2 / API key / session cookie / etc.] |
| How do services authenticate to each other?       | [mTLS / service tokens / shared secret]    |
| What authorization model is used?                 | [RBAC / ABAC / ACL / custom]               |
| Are there admin or elevated-privilege operations? | [Yes -- describe / No]                     |
| How are permissions assigned and revoked?         | [Describe process]                         |

---

## 4. Input Validation Approach

*Describe how the feature validates and sanitizes input.*

| Input Surface              | Validation Strategy                         | Sanitization Applied           |
|----------------------------|---------------------------------------------|--------------------------------|
| [API request body]         | [Schema validation, type checking]          | [HTML encoding, parameterized queries] |
| [File upload]              | [Type whitelist, size limit, virus scan]    | [Rename, isolate storage]      |
| [Query parameters]         | [Allowlist values, length limits]           | [Encoding before use in queries] |
| [Add rows as needed]       |                                             |                                |

---

## 5. Findings

*Record security concerns identified during the review.*

| Ref   | Finding                                     | Severity         | Recommendation                              | Status                |
|-------|---------------------------------------------|------------------|----------------------------------------------|-----------------------|
| F-001 | [Description of security concern]           | [Critical/High/Medium/Low] | [Specific remediation recommendation] | [Open/Resolved/Accepted] |
| F-002 | [Description of security concern]           | [Critical/High/Medium/Low] | [Specific remediation recommendation] | [Open/Resolved/Accepted] |
| F-003 | [Description of security concern]           | [Critical/High/Medium/Low] | [Specific remediation recommendation] | [Open/Resolved/Accepted] |
| [Add] |                                             |                  |                                              |                       |

---

## 6. Required Actions Before Approval

*List actions that must be completed before the design can be approved for implementation.*

- [ ] [Action from F-001: e.g., Add rate limiting to the public endpoint]
- [ ] [Action from F-002: e.g., Encrypt PII field at rest]
- [ ] [Action: e.g., Update threat model to include this new component]
- [ ] [Action: e.g., Add security test cases to the test plan]

---

## 7. Approval Status

| Outcome                | Value                                       |
|------------------------|---------------------------------------------|
| Review Result          | [Approved / Approved with Conditions / Rejected] |
| Conditions (if any)    | [List conditions that must be met before implementation proceeds] |
| Approved By            | [Reviewer name and role]                    |
| Approval Date          | [YYYY-MM-DD]                                |
| Re-review Required     | [Yes -- trigger: describe / No]             |

---

## Definition of Done

- [ ] Data classification completed for all data elements
- [ ] Authentication and authorization model reviewed
- [ ] Input validation approach documented and assessed
- [ ] All Critical and High findings resolved or mitigated
- [ ] Required actions completed or tracked with tickets
- [ ] Approval decision recorded with reviewer signature
- [ ] Threat model updated if new attack surfaces were identified

# System Context: [System Name]

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | YYYY-MM-DD                     |
| Owner         | [Architect or lead name]       |
| Related links | [ADR / design spec links]      |
| Status        | Draft / Reviewed / Approved    |

*C4-style system context description. Defines the system boundary, its users, and the external systems it interacts with.*

---

## System Purpose

[One to two sentences describing what this system does and the value it provides.]

---

## Users and Actors

*List all human users and automated actors that interact with the system.*

| Actor                 | Role                        | Interaction                          |
|-----------------------|-----------------------------|--------------------------------------|
| [e.g., End user]      | [e.g., Customer]           | [e.g., Browses catalog, places orders] |
| [e.g., Admin]         | [e.g., Operations staff]   | [e.g., Manages configuration, views reports] |
| [e.g., Scheduler]     | [e.g., Automated job]      | [e.g., Triggers nightly data sync]   |

---

## External Systems

*List all systems outside the boundary that this system communicates with.*

| System                  | Purpose                      | Protocol        | Data Exchanged               |
|-------------------------|------------------------------|-----------------|------------------------------|
| [e.g., Payment gateway] | [e.g., Process payments]    | [e.g., REST/HTTPS] | [e.g., Payment requests, confirmations] |
| [e.g., Email service]   | [e.g., Send notifications]  | [e.g., SMTP/API]   | [e.g., Notification payloads] |
| [e.g., Identity provider]| [e.g., Authenticate users] | [e.g., OIDC]       | [e.g., Tokens, user claims]  |

---

## Context Diagram

*Text-based representation of the system boundary, actors, and external systems.*

```
                    [Actor A]         [Actor B]
                        |                 |
                        v                 v
                +---------------------------+
                |                           |
                |     [System Name]         |
                |                           |
                +---------------------------+
                   |          |          |
                   v          v          v
          [External Sys 1] [External Sys 2] [External Sys 3]
```

[Brief explanation of the diagram and key relationships.]

---

## Data Flows

*Describe the primary data flows crossing the system boundary.*

1. **[Flow name]:** [Actor/System] sends [data] to [System Name] via [protocol]. [System Name] responds with [data].
2. **[Flow name]:** [System Name] pushes [data] to [External System] via [protocol] when [trigger].
3. **[Flow name]:** [External System] sends [data] to [System Name] via [protocol/callback].

---

## Assumptions

*Conditions believed to be true that the design depends on.*

- [e.g., All external systems will maintain their current API versions for at least 12 months.]
- [e.g., Peak traffic will not exceed 5x the current average within the next year.]
- [e.g., Users have modern browsers with JavaScript enabled.]

---

## Constraints

*Non-negotiable boundaries imposed on the system.*

- [e.g., Must run within the existing infrastructure region for data residency compliance.]
- [e.g., Must not introduce new runtime dependencies outside the approved technology list.]
- [e.g., Must support authentication via the organization's identity provider.]

---

## Definition of Done

- [ ] System purpose is stated clearly in one to two sentences
- [ ] All users, actors, and their interactions are listed
- [ ] All external systems are documented with protocol and data exchanged
- [ ] Context diagram accurately reflects the boundary and relationships
- [ ] Primary data flows crossing the boundary are described
- [ ] Assumptions are explicit and reviewed with stakeholders
- [ ] Constraints are documented and traceable to requirements

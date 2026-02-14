# Design Specification: [Work Item Title]

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | YYYY-MM-DD                     |
| Owner         | [Architect or lead name]       |
| Related links | [Story/issue/ADR links]        |
| Status        | Draft / Reviewed / Approved    |

---

## Overview

*One to two sentences describing what this design covers and why it exists.*

[Brief description of the component or feature being designed and the problem it solves.]

---

## Interfaces

*List all APIs, events, and data contracts this component exposes or consumes.*

### Exposed APIs

| Method | Path / Name     | Description             | Auth Required |
|--------|-----------------|-------------------------|---------------|
| [GET]  | [/resource]     | [What it returns]       | [Yes/No]      |
| [POST] | [/resource]     | [What it creates]       | [Yes/No]      |

### Consumed APIs / Dependencies

| Service / System | Endpoint / Event   | Purpose                |
|------------------|--------------------|------------------------|
| [Service name]   | [Endpoint or topic] | [Why this is consumed] |

### Events

| Event Name       | Direction (Publish/Subscribe) | Payload Summary       |
|------------------|-------------------------------|-----------------------|
| [event.name]     | [Publish]                     | [Key fields]          |

---

## Data Flow

*Describe how data moves through the component from input to output.*

1. [Step 1: e.g., "Client sends request to API gateway."]
2. [Step 2: e.g., "Gateway validates token and forwards to service."]
3. [Step 3: e.g., "Service queries data store and transforms result."]
4. [Step 4: e.g., "Response returned to client."]

---

## Component Diagram

*Text-based representation of components and their relationships.*

```
[Component A] ---> [Component B] ---> [Data Store]
       |                                    ^
       v                                    |
[Component C] ------------------------------+
```

[Brief explanation of the diagram.]

---

## Non-Functional Requirements

| Attribute      | Target                                     |
|----------------|--------------------------------------------|
| Latency        | [e.g., p99 < 200ms]                       |
| Throughput     | [e.g., 1,000 requests/sec]                |
| Availability   | [e.g., 99.9% uptime]                      |
| Data retention | [e.g., 90 days hot, 1 year cold]          |
| Scalability    | [e.g., horizontal scaling to N instances] |

---

## Dependencies

*List external or internal dependencies required for this design.*

- [Dependency 1: what it is and why it is needed]
- [Dependency 2: what it is and why it is needed]

---

## Risks

| Risk                              | Likelihood | Impact | Mitigation                     |
|-----------------------------------|------------|--------|--------------------------------|
| [e.g., Third-party API downtime]  | [Medium]   | [High] | [Circuit breaker + fallback]   |
| [e.g., Data migration complexity] | [High]     | [Medium]| [Phased rollout with rollback] |

---

## Open Questions

*Items that need resolution before or during implementation.*

- [ ] [Question 1: e.g., "What is the expected peak load for the first 6 months?"]
- [ ] [Question 2: e.g., "Do we need backward compatibility with the v1 API?"]
- [ ] [Question 3]

---

## Definition of Done

- [ ] Overview clearly states the purpose and scope
- [ ] All exposed and consumed interfaces are documented
- [ ] Data flow covers the primary path end to end
- [ ] Non-functional requirements have measurable targets
- [ ] Risks are identified with likelihood, impact, and mitigation
- [ ] Open questions are captured and assigned to owners
- [ ] Design reviewed by at least one other team member

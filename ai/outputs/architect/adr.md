# ADR-NNNN: [Short Decision Title]

<!-- Replace NNNN with the next sequential number. Title should be a noun
     phrase describing the decision, e.g., "Use PostgreSQL for Primary
     Datastore" or "Adopt Event-Driven Architecture for Order Processing." -->

## Metadata

| Field         | Value                                              |
|---------------|----------------------------------------------------|
| Date          | YYYY-MM-DD                                         |
| Owner         | [Architect name or role]                           |
| Related links | [Issue/PR/ADR links]                               |
| Status        | Draft / Reviewed / Approved                        |

---

## Status

**Proposed** | Accepted | Deprecated | Superseded by [ADR-XXXX](./adr-xxxx.md)

<!-- Lifecycle: Proposed -> Accepted -> optionally Deprecated or Superseded.
     Only one status should be active. Delete the others or bold the current
     one. -->

**Date:** YYYY-MM-DD
**Decision Maker:** [Architect name or role]
**Stakeholders:** [List personas or teams who were consulted]

---

## Context

<!-- Describe the situation that motivates this decision. Include:
     - What problem or requirement triggered this decision?
     - What constraints exist (technical, organizational, timeline)?
     - What is the current state of the system relevant to this decision?
     - Any quantitative data: load estimates, SLA targets, team size, budget.

     Be specific. "We need a database" is not context. "We need to store 50M
     user records with sub-10ms read latency at p99, accessed by 3 services,
     with the team having deep PostgreSQL experience" is context. -->

[Write context here.]

---

## Decision

<!-- State the decision clearly in one or two sentences. Then explain the key
     reasoning. This section answers "what did we decide and why?"

     Use active voice: "We will use X" not "X was chosen." -->

We will [decision statement].

**Key Reasoning:**

1. [Primary reason with supporting evidence]
2. [Secondary reason]
3. [Tertiary reason if applicable]

---

## Consequences

<!-- What changes as a result of this decision? Be honest about both the
     benefits and the costs. -->

### Positive

- [Benefit 1: e.g., "Reduces query latency from ~200ms to ~15ms based on
  benchmark results."]
- [Benefit 2]

### Negative

- [Cost 1: e.g., "Adds operational complexity -- team must learn and maintain
  a new system."]
- [Cost 2]

### Neutral

- [Side effect that is neither clearly positive nor negative, e.g., "Requires
  migrating existing data, estimated at 2 days of engineering effort."]

---

## Alternatives Considered

<!-- For each alternative, explain what it is, why it was a plausible option,
     and why it was not selected. Avoid straw-man alternatives -- only list
     options that were genuinely viable. -->

### Alternative 1: [Name]

**Description:** [What this option entails.]

**Pros:**
- [Advantage]

**Cons:**
- [Disadvantage -- and why this con outweighs the pros relative to the chosen
  option]

**Reason Not Selected:** [One sentence summary.]

### Alternative 2: [Name]

**Description:** [What this option entails.]

**Pros:**
- [Advantage]

**Cons:**
- [Disadvantage]

**Reason Not Selected:** [One sentence summary.]

---

## Compliance and Security Notes

<!-- If this decision has security, privacy, or regulatory implications, note
     them here. Reference the relevant threat model or compliance requirement.
     If none, write "No compliance or security implications identified." -->

[Notes here.]

---

## Related ADRs

<!-- Link to ADRs that this decision depends on, extends, or conflicts with.
     If this ADR supersedes another, that ADR's status should be updated to
     "Superseded by ADR-NNNN." -->

- [ADR-XXXX](./adr-xxxx.md) -- [Relationship: "depends on" | "extends" |
  "supersedes" | "conflicts with"] -- [Brief note on the relationship]

---

## Review Trigger

<!-- Under what conditions should this decision be revisited? Define a
     concrete trigger, not "when things change." Examples:
     - "When write volume exceeds 10K transactions/second."
     - "When the team grows beyond 5 backend engineers."
     - "At the 6-month architecture review."  -->

This decision should be revisited when: [trigger condition].

---

## Definition of Done

- [ ] Context section includes quantitative data and concrete constraints
- [ ] Decision statement is clear, active voice, and accompanied by key reasoning
- [ ] All genuinely viable alternatives are documented with honest pros/cons
- [ ] Positive, negative, and neutral consequences are identified
- [ ] Compliance and security implications are addressed or explicitly ruled out
- [ ] Related ADRs are linked and their statuses updated if superseded
- [ ] Review trigger defines a concrete, measurable condition
- [ ] Stakeholders listed have been consulted and agree with the status
- [ ] ADR number is assigned and title is a descriptive noun phrase

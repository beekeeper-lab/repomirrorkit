# Architecture Review Checklist: [Design / Feature Name]

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | YYYY-MM-DD                     |
| Owner         | [Reviewer name or role]        |
| Related links | [Design spec / ADR / PR links] |
| Status        | Draft / Reviewed / Approved    |

*Use this checklist when reviewing a proposed design for architectural fitness. Check each item and add notes where relevant. Mark N/A for items that do not apply.*

---

## Alignment with Existing Architecture

- [ ] Design follows established architectural patterns and conventions
- [ ] Component boundaries are consistent with existing service decomposition
- [ ] No unnecessary duplication of functionality already provided elsewhere
- [ ] Technology choices align with the current technology radar / standards

**Notes:** [Any observations or concerns]

---

## API Contract Completeness

- [ ] All endpoints / interfaces are documented with method, path, and purpose
- [ ] Request and response schemas are defined with required/optional fields
- [ ] Error responses follow the standard format with meaningful codes
- [ ] Versioning strategy is specified
- [ ] Authentication and authorization requirements are stated

**Notes:** [Any observations or concerns]

---

## Data Model Fit

- [ ] Data model is consistent with existing domain entities
- [ ] Ownership of data is clear (single source of truth identified)
- [ ] Storage technology is appropriate for access patterns
- [ ] Data retention and lifecycle policies are defined
- [ ] Schema migration strategy is considered

**Notes:** [Any observations or concerns]

---

## Security Considerations

- [ ] Authentication mechanism is identified and appropriate
- [ ] Authorization rules enforce least-privilege access
- [ ] Sensitive data is encrypted at rest and in transit
- [ ] Input validation is applied at trust boundaries
- [ ] Threat model or security review is referenced where applicable

**Notes:** [Any observations or concerns]

---

## Scalability

- [ ] Design supports expected load with headroom for growth
- [ ] Stateless where possible to enable horizontal scaling
- [ ] Bottlenecks are identified with a plan to address them
- [ ] Resource limits and quotas are defined
- [ ] Caching strategy is documented where applicable

**Notes:** [Any observations or concerns]

---

## Observability

- [ ] Logging captures key events with structured, queryable fields
- [ ] Metrics are defined for latency, throughput, and error rates
- [ ] Distributed tracing is supported for cross-service requests
- [ ] Alerting thresholds and escalation paths are identified
- [ ] Health check endpoints are provided

**Notes:** [Any observations or concerns]

---

## Error Handling

- [ ] Failure modes are identified and documented
- [ ] Retry and backoff strategies are defined for transient failures
- [ ] Circuit breaker or fallback mechanisms are in place for dependencies
- [ ] Partial failure behavior is specified (graceful degradation)
- [ ] Error propagation does not leak internal details to callers

**Notes:** [Any observations or concerns]

---

## Dependency Risk

- [ ] External dependencies are identified with SLAs and fallback plans
- [ ] Internal dependencies have clear ownership and communication channels
- [ ] No circular dependencies are introduced
- [ ] Third-party libraries or services are assessed for maturity and support
- [ ] Vendor lock-in risk is evaluated and acceptable

**Notes:** [Any observations or concerns]

---

## Migration and Backwards Compatibility

- [ ] Breaking changes to existing consumers are identified
- [ ] Migration plan includes rollback steps
- [ ] Data migration is tested with representative volumes
- [ ] Feature flags or phased rollout strategy is defined
- [ ] Deprecation timeline is communicated to affected teams

**Notes:** [Any observations or concerns]

---

## Review Summary

**Overall Assessment:** [Approved / Approved with conditions / Needs revision]

**Key findings:**

1. [Finding 1]
2. [Finding 2]
3. [Finding 3]

**Required actions before approval:**

- [ ] [Action 1]
- [ ] [Action 2]

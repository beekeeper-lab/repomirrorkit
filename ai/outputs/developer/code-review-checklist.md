# Code Review Checklist: [PR / Change Reference]

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | YYYY-MM-DD                     |
| Owner         | [Reviewer name]                |
| Related links | [PR / issue links]             |
| Status        | Draft / Reviewed / Approved    |

*Structured checklist for reviewing code changes. Check each item and add notes where applicable. Mark N/A for items that do not apply to this change.*

---

## Correctness

- [ ] Logic correctly implements the stated requirements
- [ ] Edge cases are handled (nulls, empty collections, boundary values)
- [ ] Off-by-one errors are absent in loops and range operations
- [ ] Concurrency concerns are addressed if applicable (race conditions, deadlocks)
- [ ] Error paths return meaningful results and do not leave state corrupted

**Notes:** [Any observations or concerns]

---

## Readability

- [ ] Names (variables, functions, classes) clearly convey intent
- [ ] Functions are focused on a single responsibility
- [ ] Complex logic is broken into well-named helper functions
- [ ] Code structure follows project conventions and patterns
- [ ] No dead code, commented-out blocks, or debugging artifacts remain

**Notes:** [Any observations or concerns]

---

## Tests

- [ ] Tests exist for the primary success path
- [ ] Tests cover key failure and edge-case scenarios
- [ ] Test names describe the scenario and expected outcome
- [ ] Tests are deterministic (no flakiness, no dependence on external state)
- [ ] Test data is clearly defined and not copied from production

**Notes:** [Any observations or concerns]

---

## Performance

- [ ] No unnecessary database queries or N+1 query patterns
- [ ] Loops do not perform expensive operations that could be batched
- [ ] Large collections are paginated or streamed rather than loaded entirely
- [ ] Allocations are reasonable (no unbounded growth in memory)
- [ ] Caching is used appropriately and cache invalidation is handled

**Notes:** [Any observations or concerns]

---

## Security

- [ ] User input is validated and sanitized at trust boundaries
- [ ] Authentication and authorization checks are in place for protected operations
- [ ] Sensitive data is not logged, exposed in error messages, or stored in plain text
- [ ] SQL/query injection vectors are mitigated (parameterized queries or ORM usage)
- [ ] Dependencies do not introduce known vulnerabilities

**Notes:** [Any observations or concerns]

---

## Dependencies

- [ ] New dependencies are justified and documented
- [ ] License compatibility is verified for new dependencies
- [ ] Dependency versions are pinned or constrained appropriately
- [ ] No unnecessary dependencies are introduced

**Notes:** [Any observations or concerns]

---

## Documentation

- [ ] Public API changes are reflected in API documentation
- [ ] Non-obvious logic has comments explaining the "why"
- [ ] README or setup instructions are updated if the change affects them
- [ ] Changelog entry is added if required by project convention

**Notes:** [Any observations or concerns]

---

## Review Summary

**Verdict:** [Approved / Request changes / Needs discussion]

**Key feedback:**

1. [Feedback item 1]
2. [Feedback item 2]
3. [Feedback item 3]

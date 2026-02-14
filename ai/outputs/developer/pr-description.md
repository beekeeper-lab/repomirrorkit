# PR: [Short descriptive title]

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | YYYY-MM-DD                     |
| Owner         | [Author name]                  |
| Related links | [Issue / story / design links] |
| Status        | Draft / Ready for Review       |

---

## Summary

*What does this PR do and why?*

[One to three sentences explaining the change. Focus on the "why" -- the problem being solved or the feature being delivered -- not just the "what."]

---

## Changes Made

- [Change 1: e.g., "Added resource service with create/read/update operations"]
- [Change 2: e.g., "Updated API routes to expose new endpoints"]
- [Change 3: e.g., "Added migration script for new table"]
- [Change 4: e.g., "Added unit and integration tests"]

---

## Testing Done

### Automated

- [ ] Unit tests added/updated -- [brief description of coverage]
- [ ] Integration tests added/updated -- [brief description of scope]
- [ ] All existing tests pass

### Manual

- [ ] [Manual test 1: e.g., "Verified endpoint returns correct response via API client"]
- [ ] [Manual test 2: e.g., "Confirmed error handling for invalid input"]

---

## Screenshots / Recordings

*Include if this PR changes UI behavior. Remove this section if not applicable.*

| Before | After |
|--------|-------|
| [screenshot or description] | [screenshot or description] |

---

## Risks and Rollback Plan

- **Risk:** [e.g., "Migration adds a new column; rollback requires a reverse migration"]
- **Rollback:** [e.g., "Revert this PR and run the down migration script"]
- **Feature flag:** [e.g., "Behind flag `enable_new_resource` -- can disable without deploy"]

---

## Related Issues

- Closes [#issue-number]
- Related to [#issue-number]

---

## Reviewer Checklist

*For the reviewer to complete during review.*

- [ ] Changes match the PR summary and related issue
- [ ] Code is readable and follows project conventions
- [ ] Tests cover the primary path and key edge cases
- [ ] No secrets, credentials, or sensitive data included
- [ ] Database migrations are reversible
- [ ] Error handling is appropriate and does not leak internals
- [ ] Documentation is updated if public interfaces changed

# Task 003: Developer — Unit Tests

**Owner:** Developer
**Status:** Done
**Depends On:** 002

## Objective

Write unit tests for all 7 bean template types in `tests/unit/test_templates.py`.

## Test Coverage

- Each template type renders with sample Surface data
- Frontmatter contains required fields (id, type, title, source_refs, traceability, status)
- Each template produces the correct number of markdown sections
- `render_bean()` dispatches correctly
- `status: draft` in all generated frontmatter

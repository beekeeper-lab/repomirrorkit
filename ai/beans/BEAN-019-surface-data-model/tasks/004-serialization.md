# Task 004: Implement to_dict() JSON serialization

| Field | Value |
|-------|-------|
| **Task ID** | 004 |
| **Bean** | BEAN-019 |
| **Owner** | Developer |
| **Status** | Pending |

## Objective
Implement to_dict() on all surface classes and SurfaceCollection for JSON output.

## Acceptance Criteria
- All surfaces serialize to plain dicts via to_dict()
- Output is JSON-serializable (json.dumps works without errors)
- Nested objects (SourceRef, field lists) are properly serialized

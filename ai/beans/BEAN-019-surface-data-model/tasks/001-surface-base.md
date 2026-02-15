# Task 001: Define Surface base dataclass and SourceRef

| Field | Value |
|-------|-------|
| **Task ID** | 001 |
| **Bean** | BEAN-019 |
| **Owner** | Developer |
| **Status** | Pending |

## Objective
Define `SourceRef` (file path + line range) and `Surface` base dataclass with `source_refs`, `name`, `surface_type` fields.

## Acceptance Criteria
- `SourceRef` has `file_path: str`, `start_line: int | None`, `end_line: int | None`
- `Surface` has `name: str`, `surface_type: str`, `source_refs: list[SourceRef]`
- Both are frozen dataclasses with `to_dict()` method

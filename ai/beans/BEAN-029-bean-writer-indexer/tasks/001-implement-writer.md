# Task 001: Implement writer.py — bean file generation

| Field | Value |
|-------|-------|
| **Task** | Implement writer.py |
| **Owner** | Developer |
| **Status** | Done |
| **Depends On** | — |

## Objective

Implement `src/repo_mirror_kit/harvester/beans/writer.py` with:
- `slugify()` function for generating URL-safe slugs from surface names
- `WrittenBean` dataclass for recording written beans
- `write_beans()` function that iterates a SurfaceCollection, renders each surface, and writes to disk

## Acceptance Criteria

- [x] Iterates SurfaceCollection in deterministic order (routes → components → APIs → models → auth → config → crosscutting)
- [x] Generates sequential bean IDs: BEAN-001, BEAN-002, etc.
- [x] Slugs are lowercase, hyphenated, no special chars
- [x] Files written as `beans/BEAN-###-<slug>.md`
- [x] Resume mode: skips already-written beans via StateManager
- [x] Checkpointing: calls `state.record_bean()` after each bean
- [x] Logs progress with structlog
- [x] Empty collections produce no files

## Implementation Notes

- Used `re.sub(r"[^a-z0-9]+", "-", slug)` for slug generation
- WrittenBean is a frozen dataclass with `skipped` flag for resume tracking
- Logger uses standard `logging.getLogger(__name__)` per project convention

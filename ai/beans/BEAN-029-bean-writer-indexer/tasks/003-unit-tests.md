# Task 003: Write unit tests for writer and indexer

| Field | Value |
|-------|-------|
| **Task** | Write unit tests |
| **Owner** | Developer |
| **Status** | Done |
| **Depends On** | Task 002 |

## Objective

Write comprehensive unit tests covering:
- Slug generation edge cases
- Bean file writing, ordering, and numbering
- Resume/skip logic
- Checkpoint behavior
- Index generation and content
- Templates directory creation

## Test Coverage

### test_writer.py (30 tests)
- **TestSlugify** (12 tests): basic, numbers, special chars, unicode, empty, edge cases
- **TestWriteBeans** (10 tests): file creation, numbering, ordering, filenames, content, empty collection
- **TestWriteBeansResume** (4 tests): skip logic, disk state, no-overwrite
- **TestWriteBeansCheckpoint** (2 tests): interval behavior, count tracking
- **TestWrittenBean** (2 tests): dataclass fields, skipped flag

### test_indexer.py (16 tests)
- **TestGenerateIndex** (9 tests): file creation, content, ordering, empty list
- **TestGenerateTemplatesDir** (7 tests): directory creation, files, content, spec refs, idempotency

## Results

- All 46 tests pass
- No regressions in existing 1015 tests

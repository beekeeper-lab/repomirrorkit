# Task 002: Unit Tests for git_ops.py

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Status** | Pending |
| **Depends On** | Task 001 |

## Objective

Write unit tests in `tests/unit/test_git_ops.py` covering:
- Successful clone
- Ref checkout (branch/tag/SHA)
- Missing git on PATH
- Invalid ref produces clear error
- Symlink safety (outside-repo symlinks skipped)
- Line ending normalization
- State checkpoint written after Stage A

## Approach

- Mock subprocess calls using unittest.mock.patch
- Use tmp_path fixture for temp directories
- Follow existing test patterns from test_state.py

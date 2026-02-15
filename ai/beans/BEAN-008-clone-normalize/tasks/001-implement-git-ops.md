# Task 001: Implement git_ops.py

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Status** | In Progress |
| **Depends On** | BEAN-004 (Harvester Package), BEAN-006 (State Management) |

## Objective

Implement `src/repo_mirror_kit/harvester/git_ops.py` with:
- `clone_repository(url, ref, workdir)` — clone to temp directory
- Ref checkout after clone (branch/tag/SHA)
- Default branch if no ref specified
- Clear error on invalid ref
- Line ending normalization (CRLF → LF)
- Symlink safety (skip symlinks pointing outside repo)
- Missing git detection
- Structured logging via structlog
- State checkpoint via StateManager

## Acceptance Criteria

- All acceptance criteria from bean.md are met
- Code follows Python stack conventions (ruff, mypy, type hints, Google docstrings)
- No subprocess calls without proper error handling

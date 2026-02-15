# Task 002: Implement CLI Click Command

| Field | Value |
|-------|-------|
| **Task ID** | 002 |
| **Status** | Pending |
| **Owner** | Developer |
| **Depends On** | 001 |

## Objective

Implement the Click-based CLI in `src/repo_mirror_kit/harvester/cli.py` with `main` command group and `harvest` subcommand.

## Acceptance Criteria

- [ ] `main` Click group entry point
- [ ] `harvest` subcommand with all arguments from spec section 3.2
- [ ] --repo is required, missing produces exit code 3
- [ ] --include and --exclude accept comma-separated glob patterns
- [ ] --log-level accepts debug/info/warn/error (case-insensitive)
- [ ] Invalid --log-level produces exit code 3
- [ ] Exit codes: 0 (success), 2 (gaps), 3 (invalid input), 5 (unexpected error)
- [ ] Console script entry point in pyproject.toml

# Task 001: Implement HarvestConfig Dataclass

| Field | Value |
|-------|-------|
| **Task ID** | 001 |
| **Status** | Pending |
| **Owner** | Developer |
| **Depends On** | — |

## Objective

Implement the `HarvestConfig` dataclass in `src/repo_mirror_kit/harvester/config.py` with all fields from the spec section 3.2 and proper default values.

## Acceptance Criteria

- [ ] `HarvestConfig` is a frozen dataclass
- [ ] Fields: repo (str), ref (str | None), out (Path | None), include (tuple[str, ...]), exclude (tuple[str, ...]), max_file_bytes (int), resume (bool), fail_on_gaps (bool), log_level (str)
- [ ] Default exclude globs: node_modules, dist, build, .git, .venv, coverage, **/*.min.*
- [ ] Default max_file_bytes: 1_000_000
- [ ] Default fail_on_gaps: True
- [ ] Default log_level: "info"
- [ ] Validation method for log_level
- [ ] Proper type hints throughout

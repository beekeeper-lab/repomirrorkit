# Task 002: Implement indexer.py — master index and templates dir

| Field | Value |
|-------|-------|
| **Task** | Implement indexer.py |
| **Owner** | Developer |
| **Status** | Done |
| **Depends On** | Task 001 |

## Objective

Implement `src/repo_mirror_kit/harvester/beans/indexer.py` with:
- `generate_index()` — creates `beans/_index.md` with master summary table
- `generate_templates_dir()` — creates `beans/_templates/` with 7 template description files

## Acceptance Criteria

- [x] `beans/_index.md` lists all beans with ID, title, type, status
- [x] Index preserves generation order
- [x] `beans/_templates/` contains 7 template files (one per surface type)
- [x] Template files reference spec sections
- [x] Handles empty bean lists
- [x] Creates parent directories as needed
- [x] Idempotent — running twice produces same result

## Implementation Notes

- Index uses markdown table format
- Template files contain descriptions extracted from render function docstrings
- Both functions log completion events

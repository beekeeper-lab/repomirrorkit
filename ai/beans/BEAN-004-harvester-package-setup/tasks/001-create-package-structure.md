# Task 001: Create Harvester Package Structure

| Field | Value |
|-------|-------|
| **Owner** | Developer |
| **Status** | Pending |
| **Depends On** | — |

## Objective

Create the `src/repo_mirror_kit/harvester/` package with all subpackages and placeholder modules.

## Acceptance Criteria

- `src/repo_mirror_kit/harvester/__init__.py` exists
- Subpackages: `detectors/`, `analyzers/`, `beans/`, `reports/`, `runtime_verify/`
- Placeholder modules: `cli.py`, `config.py`, `state.py`, `inventory.py`, `git_ops.py`
- All `.py` files have `from __future__ import annotations`
- All files follow Python stack conventions

# BEAN-009: File Inventory (Stage B)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-009 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-14 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

Before the harvester can analyze a repository, it needs a complete inventory of all files: their paths, sizes, extensions, content hashes, and category guesses. This inventory drives the include/exclude filtering, feeds into the detector system, and provides the ordered worklist that ensures deterministic, complete iteration.

## Goal

Implement the file inventory module that scans a cloned repository, applies include/exclude filters, categorizes files, computes fast hashes, and emits `reports/inventory.json`.

## Scope

### In Scope
- Implement `src/repo_mirror_kit/harvester/inventory.py`
- Recursive file scanning of the cloned repo working directory
- Apply `--include` and `--exclude` glob filters
- Default excludes: `node_modules, dist, build, .git, .venv, coverage, **/*.min.*`
- Skip files exceeding `--max-file-bytes` (default: 1,000,000)
- For each file: record path (repo-relative), size, extension, fast hash (e.g., xxhash or MD5)
- Category guessing based on extension and path patterns (source, config, test, asset, documentation, migration)
- Produce ordered worklist for deterministic iteration
- Emit `reports/inventory.json` with the complete file inventory
- Record skipped files with reason (excluded, too large, binary)
- Write state checkpoint after Stage B completion
- Unit tests for filtering, categorization, hash computation, skip recording

### Out of Scope
- Stack detection (BEAN-010 — Detector Framework)
- Deep content analysis of files (Stage C analyzers)
- Binary file content analysis
- Git history analysis (only current working tree)

## Acceptance Criteria

- [ ] `inventory.scan(workdir, config)` returns a structured inventory of all included files
- [ ] Default exclude globs filter out `node_modules`, `dist`, `build`, `.git`, `.venv`, `coverage`, `**/*.min.*`
- [ ] Custom `--include` globs restrict scanning to matched files only
- [ ] Custom `--exclude` globs add to the default exclude list
- [ ] Files exceeding `--max-file-bytes` are skipped with reason recorded
- [ ] Each file entry includes: path, size, extension, hash, category
- [ ] Categories include at minimum: source, config, test, asset, documentation, migration
- [ ] `reports/inventory.json` is written with the complete inventory
- [ ] Skipped files are recorded in the inventory with skip reason
- [ ] File iteration order is deterministic (sorted by path)
- [ ] State checkpoint written after Stage B completion
- [ ] Unit tests cover: glob filtering, size filtering, categorization, hash computation
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | | | | Pending |

## Notes

- Depends on BEAN-004 (Harvester Package Setup), BEAN-006 (State Management & Resume), BEAN-008 (Clone & Normalize for the workdir).
- Reference: Spec section 6, Stage B (Inventory & detection) and section 9.1 (Deterministic iteration).
- The inventory produces the ordered worklist that all subsequent analyzers iterate over. Deterministic ordering is critical for resume support.
- Consider using `xxhash` for fast hashing (add as dependency) or fall back to `hashlib.md5` if we want to minimize dependencies.
- The inventory is also consumed by the detector system (BEAN-010) to identify stack signals.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 |      |       |          |           |            |

| Metric | Value |
|--------|-------|
| **Total Tasks** | — |
| **Total Duration** | — |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |

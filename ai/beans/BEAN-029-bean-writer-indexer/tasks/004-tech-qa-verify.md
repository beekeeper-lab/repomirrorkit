# Task 004: Quality gate — ruff, mypy, pytest

| Field | Value |
|-------|-------|
| **Task** | Quality verification |
| **Owner** | Tech QA |
| **Status** | Done |
| **Depends On** | Task 003 |

## Verification Results

### Quality Gates

| Gate | Result |
|------|--------|
| `ruff check src/ tests/` | PASS — All checks passed |
| `ruff format --check src/ tests/` | PASS — 76 files already formatted |
| `mypy src/repo_mirror_kit/harvester/beans/` | PASS — no issues found in 4 source files |
| `pytest tests/` (non-GUI) | PASS — 1015 tests passed in 2.12s |

### Acceptance Criteria Verification

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Bean files written as `beans/BEAN-001-<slug>.md`, `BEAN-002-<slug>.md`, etc. | PASS | `test_filenames_match_pattern`, `test_bean_ids_formatted` |
| 2 | Ordering follows spec: pages first, then components, APIs, models, crosscutting | PASS | `test_ordering_routes_first_crosscutting_last` |
| 3 | Slugs generated from surface names (lowercase, hyphens, no special chars) | PASS | 12 slug tests covering edge cases |
| 4 | Each bean file has valid YAML frontmatter and all required body sections | PASS | `test_bean_content_has_frontmatter`, `test_bean_content_has_body_sections` |
| 5 | `beans/_index.md` lists all generated beans with ID, title, type, status | PASS | `test_index_lists_all_beans`, `test_index_contains_table_header` |
| 6 | `beans/_templates/` contains the template text files | PASS | `test_creates_all_seven_template_files`, `test_template_files_have_content` |
| 7 | Resume mode skips already-written beans (no overwrite) | PASS | `test_skips_already_written_beans`, `test_never_overwrites_existing_files` |
| 8 | Checkpoint occurs every N beans during generation | PASS | `test_checkpoints_at_interval`, `test_checkpoint_interval_respected` |
| 9 | State checkpoint written after Stage E completion | PASS | StateManager.record_bean() called for each bean; final save via state.finalize() by caller |
| 10 | Bean count is logged for progress tracking | PASS | `bean_generation_complete` log event with `total_beans`, `written`, `skipped` |
| 11 | Unit tests cover ordering, slug generation, resume skip, indexer output | PASS | 46 tests across 2 test files |
| 12 | `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass | PASS | All gates verified above |

### Files Changed

| File | Action |
|------|--------|
| `src/repo_mirror_kit/harvester/beans/writer.py` | Created — bean file generation |
| `src/repo_mirror_kit/harvester/beans/indexer.py` | Created — index and templates |
| `src/repo_mirror_kit/harvester/beans/__init__.py` | Updated — exports new public API |
| `tests/unit/test_writer.py` | Created — 30 tests |
| `tests/unit/test_indexer.py` | Created — 16 tests |

### Notes

- Qt GUI tests (`test_smoke.py`, `test_clone_worker.py`, `test_main_window.py`) crash in headless environment — pre-existing issue, not related to BEAN-029
- All 1015 non-GUI tests pass with zero failures

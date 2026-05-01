# BEAN-050 Task 02: Fix Pre-existing ruff and pytest Gate Failures

| Field | Value |
|-------|-------|
| **Owner** | developer |
| **Status** | Done |
| **Started** | 2026-05-01 11:10 |
| **Completed** | 2026-05-01 11:11 |
| **Duration** | 1m |
| **Depends On** | 01 |

## Goal

Resolve two pre-existing failures (discovered during BEAN-058 Tech-QA verification) that block BEAN-050's "lint clean" and "all tests pass" Acceptance Criteria. Per `/long-run`'s `TestFailure` policy ("Attempt to fix; if unresolvable, report and stop"), these are fixed inline as part of BEAN-050.

## Inputs

- BEAN-058 Verification section (documents both failures)
- `tests/unit/test_generator.py::TestAssembler::test_result_counts` (the failing test)
- `src/repo_mirror_kit/harvester/generator/assembler.py:91-101` (the `.claude/` infra copy step that the test does not account for)
- `uv run ruff check src/ tests/` output

## Acceptance Criteria

- [ ] `uv run ruff check --fix src/ tests/` applied; remaining manual fixes if any
- [ ] `uv run ruff check src/ tests/` exits 0 with no errors
- [ ] `tests/unit/test_generator.py::TestAssembler::test_result_counts` updated to either:
   (a) count the copied `.claude/` infrastructure files in its expected total, OR
   (b) exclude infra copy files from the assertion (e.g., assert generated_files contains agents + stacks + CLAUDE.md as a subset rather than equality)
- [ ] `uv run pytest tests/unit/test_generator.py` passes cleanly
- [ ] No source-of-truth code in `src/` modified — fixes are limited to the affected test file and any auto-fixable import ordering in test files

## Definition of Done

- Both gates clean: `ruff check` exits 0, `pytest` exits 0 (excluding the BEAN-050 integration tests, which are tested separately)
- Changes committed on the feature branch
- Brief note added to BEAN-050's Notes section explaining the inline scope expansion

## Notes

- ruff errors are all `I001` (import-block format), 12 total, all auto-fixable.
- The test_result_counts fix should preserve the test's intent — verifying that agents/stacks/CLAUDE.md ARE among the generated files — without requiring strict equality with a count that ignores infrastructure copy.
- Filing as a separate task (rather than folding into Task 01) keeps the audit trail clear: fixture/test work vs. inline gate cleanup are distinct responsibilities.

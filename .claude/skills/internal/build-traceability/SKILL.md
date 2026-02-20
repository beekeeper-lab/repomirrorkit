# Skill: Build Traceability

## Description

Maps user stories and their acceptance criteria to test cases, producing a
traceability matrix that shows coverage relationships and identifies gaps.
Every acceptance criterion should trace forward to at least one test case,
and every test case should trace back to at least one requirement. This
bidirectional mapping ensures nothing is tested without purpose and nothing
is required without verification.

## Trigger

- Invoked by the `/build-traceability` slash command.
- Called by the Tech-QA persona during test planning or after new stories are added.
- Should be re-run whenever the story set or test set changes significantly.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| stories_dir | Directory path | Yes | Directory containing user story files (e.g., `ai/outputs/ba/user-stories/`) |
| tests_dir | Directory path | No | Directory containing test case files; defaults to `ai/outputs/tech-qa/` |
| existing_matrix | File path | No | Previous traceability matrix to update incrementally |

## Process

1. **Inventory stories and criteria** -- Parse all story files in the stories directory. Extract each acceptance criterion as a discrete traceable item with a unique identifier (e.g., `STORY-001-AC-01`).
2. **Inventory test cases** -- Parse all test case files. Extract each test case with its identifier and the criteria it claims to verify.
3. **Build forward trace** -- For each acceptance criterion, find all test cases that cover it. A criterion with zero test cases is a **coverage gap**.
4. **Build reverse trace** -- For each test case, find all acceptance criteria it maps to. A test case with zero criteria links is an **orphaned test** (tests something not required).
5. **Compute coverage metrics** -- Calculate: total criteria, covered criteria, gap count, coverage percentage. Separately compute: total tests, linked tests, orphaned test count.
6. **Identify risk areas** -- Flag criteria with high business impact that have thin coverage (only one test case) or no coverage.
7. **Produce traceability matrix** -- Generate a matrix table showing criteria on one axis and test cases on the other, with coverage indicators.
8. **Produce gap report** -- List all coverage gaps and orphaned tests with recommended actions.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| traceability_matrix | Markdown file | Criteria-to-test mapping table with coverage indicators |
| coverage_summary | Section in matrix | Metrics: total criteria, covered, gaps, coverage percentage |
| gap_report | Section in matrix | List of uncovered criteria and orphaned tests with recommendations |

## Quality Criteria

- Every acceptance criterion from every story is represented in the matrix -- none are silently dropped.
- Coverage gaps are clearly identified with the specific criterion that lacks test coverage.
- Orphaned tests are flagged but not treated as errors -- they may be exploratory or regression tests.
- The coverage percentage is accurate and computed from actual trace links, not file counts.
- The matrix is readable: for projects with many stories, group by epic or feature area.
- Recommendations for gaps are specific: "Write a test for STORY-003-AC-02 covering the edge case where..." not just "add tests."

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `StoriesDirNotFound` | Stories directory does not exist | Check the path; ensure stories have been created |
| `NoStoriesFound` | Stories directory exists but contains no story files | Run `/internal:notes-to-stories` first to create stories |
| `NoCriteriaFound` | Stories exist but none contain parseable acceptance criteria | Add acceptance criteria to the story files |
| `TestsDirNotFound` | Tests directory does not exist | Create test cases first or specify a different path |

## Dependencies

- User stories with acceptance criteria (produced by the BA persona or `/internal:notes-to-stories` skill)
- Test cases (produced by the Tech-QA persona)
- No external tooling required; this skill operates on markdown files

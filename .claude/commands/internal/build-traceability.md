# /build-traceability Command

Claude Code slash command that builds a requirements-to-tests traceability matrix.

## Purpose

Map every acceptance criterion to the test cases that verify it, and every test case back to the criteria it covers. Produces a matrix showing coverage and a gap report highlighting untested requirements and orphaned tests. Essential for regulated posture projects; valuable for any project that needs confidence in test coverage.

## Usage

```
/build-traceability [--stories <dir>] [--tests <dir>]
```

All arguments are optional with sensible defaults.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Stories directory | `--stories` flag or `ai/outputs/ba/user-stories/` | Yes (defaults applied) |
| Tests directory | `--tests` flag or `ai/outputs/tech-qa/` | No |
| Existing matrix | `--update` flag | No |

## Process

1. **Parse stories** -- Extract acceptance criteria from all story files.
2. **Parse tests** -- Extract test cases and their criteria links.
3. **Build matrix** -- Map criteria to tests (forward) and tests to criteria (reverse).
4. **Compute coverage** -- Calculate coverage percentage and identify gaps.
5. **Write output** -- Produce the matrix, summary, and gap report.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Traceability matrix | `ai/outputs/tech-qa/traceability-matrix.md` | Coverage matrix with metrics and gap report |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--stories <dir>` | `ai/outputs/ba/user-stories/` | Directory containing story files |
| `--tests <dir>` | `ai/outputs/tech-qa/` | Directory containing test case files |
| `--update <path>` | None | Update an existing matrix incrementally |
| `--output <path>` | `ai/outputs/tech-qa/traceability-matrix.md` | Override the output file path |
| `--format <table\|list>` | `table` | Matrix format: table for small sets, list for large sets |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `StoriesDirNotFound` | Stories directory does not exist | Check the path or run `/internal:notes-to-stories` first |
| `NoStoriesFound` | No story files in the directory | Create stories before building traceability |
| `NoCriteriaFound` | Stories lack parseable acceptance criteria | Add acceptance criteria to story files |

## Examples

**Build with defaults:**
```
/build-traceability
```
Reads stories from `ai/outputs/ba/user-stories/` and tests from `ai/outputs/tech-qa/`, produces the matrix.

**Custom directories:**
```
/build-traceability --stories docs/requirements/ --tests tests/
```
Uses custom locations for stories and tests.

**Update existing matrix:**
```
/build-traceability --update ai/outputs/tech-qa/traceability-matrix.md
```
Incrementally updates the matrix after new stories or tests are added.

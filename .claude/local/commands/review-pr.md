# /review-pr Command

Claude Code slash command that performs a structured code review.

## Purpose

Run a repeatable, checklist-driven code review covering readability, correctness, maintainability, convention consistency, test coverage, and security. Produces a clear verdict (ship / ship with comments / request changes) with actionable, line-level feedback. Optionally enforces green checks (tests + lint) as a gate before review begins.

## Usage

```
/review-pr [diff-or-pr] [--skip-checks] [--checklist <path>]
```

- `diff-or-pr` -- A diff file, directory of changed files, PR number, or PR URL. Defaults to the current branch's uncommitted changes.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Code changes | Positional argument or current branch diff | Yes |
| Project conventions | Auto-detected from `ai/context/project.md` | No |
| Review checklist | `--checklist` flag or default template | No |

## Process

1. **Gate check** -- Verify tests and lint pass (unless `--skip-checks`).
2. **Parse diff** -- Understand scope and purpose of changes.
3. **Review** -- Check readability, correctness, maintainability, consistency, tests, security.
4. **Verdict** -- Assign ship / ship-with-comments / request-changes.
5. **Report** -- Produce findings with file:line references.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Review report | `ai/outputs/code-quality-reviewer/review-report.md` | Findings, verdict, and summary |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--skip-checks` | `false` | Skip test and lint prerequisite checks |
| `--checklist <path>` | Default template | Custom review checklist |
| `--output <path>` | `ai/outputs/code-quality-reviewer/` | Override the output directory |
| `--self-review` | `false` | Self-review mode: same rigor, author-facing language |
| `--security-only` | `false` | Only run the security checks, skip other categories |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoDiffProvided` | No changes found | Provide a diff, PR reference, or make changes on the current branch |
| `TestsFailing` | Tests fail and `--skip-checks` not set | Fix failing tests first |
| `LintFailing` | Lint errors and `--skip-checks` not set | Fix lint errors first |
| `EmptyDiff` | No changes in the diff | Verify the correct branch or commit range |

## Examples

**Review current branch changes:**
```
/review-pr
```
Reviews uncommitted changes against project conventions.

**Review a specific PR:**
```
/review-pr 42
```
Fetches PR #42 and runs the full review checklist.

**Self-review before submitting:**
```
/review-pr --self-review
```
Runs the same checklist but frames feedback as self-improvement rather than reviewer-to-author.

**Security-focused review:**
```
/review-pr --security-only
```
Only checks for security red flags: injection, secrets, auth issues, OWASP Top 10.

**Skip prerequisite checks:**
```
/review-pr --skip-checks
```
Skips the test/lint gate; useful when reviewing design-only changes or documentation.

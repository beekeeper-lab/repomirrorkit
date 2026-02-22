# Skill: Review PR

## Description

Performs a structured code review following a repeatable checklist: readability,
correctness, maintainability, consistency with project conventions, test
coverage, and security red flags. The review produces a verdict (ship, ship
with comments, or request changes) with specific, actionable feedback tied
to file locations. This skill can require "green checks" (passing tests and
lint) as a prerequisite before the human-judgment review begins.

## Trigger

- Invoked by the `/review-pr` slash command.
- Called by the Code Quality Reviewer persona after a PR is submitted.
- Can be invoked by any persona for self-review before requesting formal review.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| diff | Text, file path, or PR reference | Yes | The code changes to review: a diff file, a directory of changed files, or a PR number/URL |
| project_conventions | File path | No | Project conventions doc; auto-detected from `ai/context/project.md` or `CLAUDE.md` |
| stack_context | File path | No | Stack conventions; auto-detected from composition spec |
| review_checklist | File path | No | Custom review checklist; defaults to the Code Quality Reviewer's template |

## Process

1. **Verify prerequisites** -- Check that tests pass and linting is clean. If either fails, return early with a "fix before review" response listing the failures. Skip this step if `--skip-checks` is set.
2. **Read the diff** -- Parse the changeset to understand what files were modified, added, or deleted. Build a mental model of the change's scope and purpose.
3. **Check readability** -- Evaluate naming (variables, functions, classes), code organization, comment quality, and whether the code communicates intent clearly. Flag clever-but-obscure patterns.
4. **Check correctness** -- Look for logic errors, off-by-one bugs, null/undefined handling, race conditions, resource leaks, and incorrect API usage. Verify edge cases are handled.
5. **Check maintainability** -- Evaluate coupling, cohesion, abstraction level, and whether the change will be easy to modify in the future. Flag code that is hard to test or tightly coupled to implementation details.
6. **Check consistency** -- Compare against project conventions: naming patterns, file organization, error handling approach, logging patterns, import ordering. Flag deviations.
7. **Check test coverage** -- Verify that new behavior has corresponding tests. Check that tests are meaningful (not just asserting true) and cover both happy path and edge cases.
8. **Check security** -- Scan for injection vulnerabilities (SQL, XSS, command), hardcoded secrets, improper authentication/authorization, insecure deserialization, and OWASP Top 10 patterns.
9. **Produce review verdict** -- Assign one of three verdicts:
   - **Ship**: No issues found; approve immediately.
   - **Ship with comments**: Minor suggestions that don't block merging; author can address at their discretion.
   - **Request changes**: Issues that must be fixed before merging; the PR cannot ship as-is.
10. **Write review report** -- Produce a structured report with the verdict, per-file findings (file:line references), and a summary.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| review_report | Markdown file | Structured review with verdict, findings, and file:line references |
| verdict | Enum: `ship`, `ship-with-comments`, `request-changes` | Overall review decision |
| findings | List in report | Per-file, per-line findings categorized by type (readability, correctness, etc.) |

## Quality Criteria

- Every finding references a specific file and line number -- no vague "the code could be better" comments.
- Findings are categorized (readability, correctness, maintainability, consistency, tests, security) so the author can triage by type.
- The verdict is consistent with the findings: `ship` means zero blocking issues; `request-changes` means at least one blocking issue exists.
- Security findings are always blocking (request-changes) regardless of other findings.
- The review distinguishes between "must fix" (blocking) and "consider" (non-blocking) suggestions.
- The review does not nitpick style issues that a linter should catch -- if a linter rule exists for it, reference the rule instead of manually flagging it.
- Self-review mode produces the same quality as formal review -- no reduced standards.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoDiffProvided` | No diff, file list, or PR reference supplied | Provide the changes to review |
| `TestsFailing` | Test suite fails (and `--skip-checks` not set) | Fix the test failures before requesting review |
| `LintFailing` | Linter reports errors (and `--skip-checks` not set) | Fix lint errors before requesting review |
| `EmptyDiff` | The diff contains no changes | Nothing to review; verify the correct branch or commit range |

## Dependencies

- Code Quality Reviewer persona's review template (`personas/code-quality-reviewer/templates/`) if available
- Project conventions from `ai/context/project.md` or `CLAUDE.md`
- Stack conventions from the composition spec
- Test runner and linter for prerequisite checks (optional, skippable)

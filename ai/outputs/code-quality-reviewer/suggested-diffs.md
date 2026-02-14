# Suggested Diffs

## Metadata

| Field         | Value                              |
|---------------|------------------------------------|
| Date          | [YYYY-MM-DD]                       |
| Owner         | [Reviewer name]                    |
| Related Links | [PR/Issue/ADR references]          |
| Status        | Draft / Reviewed / Approved        |

---

## Purpose

*Present proposed code changes as before/after pairs with context and rationale. This template is for reviewers to communicate specific fix suggestions clearly.*

## Guidance for Presenting Diffs

*Use fenced code blocks with the file's language for syntax highlighting. Show enough surrounding context (3-5 lines) so the author can locate the change. Mark removed lines with `- ` prefix and added lines with `+ ` prefix in a `diff` block, or show separate "before" and "after" blocks.*

---

## Suggestion 1

### Context

- **File:** [File path]
- **Lines:** [Start line - End line]
- **Why:** [What problem does this change address?]

### Original

```
[Paste the original code with surrounding context]
```

### Suggested

```
[Paste the suggested replacement code]
```

### Explanation

[Describe what changed and why it is an improvement]

### Risk Assessment

- **What could this break?** [Describe any side effects or downstream impacts]
- **Confidence:** [High / Medium / Low]

### Tests to Verify

- [ ] [Test to run or write to confirm the change is safe]
- [ ] [Additional verification step]

---

## Suggestion 2

### Context

- **File:** [File path]
- **Lines:** [Start line - End line]
- **Why:** [What problem does this change address?]

### Original

```
[Paste the original code with surrounding context]
```

### Suggested

```
[Paste the suggested replacement code]
```

### Explanation

[Describe what changed and why]

### Risk Assessment

- **What could this break?** [Describe any side effects]
- **Confidence:** [High / Medium / Low]

### Tests to Verify

- [ ] [Test to run or write]

---

*Copy the suggestion block above for additional diffs.*

## Summary

| # | File                | Change Type                  | Risk   |
|---|---------------------|------------------------------|--------|
| 1 | [File path]         | [Bug fix / Refactor / Perf]  | [H/M/L]|
| 2 | [File path]         | [Bug fix / Refactor / Perf]  | [H/M/L]|

---

## Definition of Done

- [ ] Each suggestion includes before/after code with sufficient context
- [ ] Explanation clearly states the rationale for each change
- [ ] Risk assessment provided for every suggestion
- [ ] Verification tests identified for each change

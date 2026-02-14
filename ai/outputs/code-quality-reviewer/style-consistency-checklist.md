# Style Consistency Checklist

## Metadata

| Field         | Value                              |
|---------------|------------------------------------|
| Date          | [YYYY-MM-DD]                       |
| Owner         | [Reviewer name]                    |
| Related Links | [PR/Issue/ADR references]          |
| Status        | Draft / Reviewed / Approved        |

---

## Review Context

- **PR / Change Reference:** [PR number or link]
- **Author:** [Developer name]
- **Project Style Guide:** [Link to project style guide or linter config]

*Check each item against the project's established conventions. Mark items as Pass, Fail, or N/A.*

---

## Naming Conventions

| Item                                                         | Result      | Notes        |
|--------------------------------------------------------------|-------------|--------------|
| Variable names follow project convention (e.g., camelCase, snake_case) | [P/F/N/A] | |
| Function/method names are descriptive verbs or verb phrases  | [P/F/N/A]   | |
| Class/type names are descriptive nouns in project convention | [P/F/N/A]   | |
| Constants use project convention (e.g., UPPER_SNAKE_CASE)    | [P/F/N/A]   | |
| File names follow project naming pattern                     | [P/F/N/A]   | |
| No abbreviations or acronyms without prior project precedent | [P/F/N/A]   | |

## Code Structure

| Item                                                         | Result      | Notes        |
|--------------------------------------------------------------|-------------|--------------|
| Functions stay below team length threshold (default: 50 lines)| [P/F/N/A]  | |
| Functions have no more than team max parameters (default: 5) | [P/F/N/A]   | |
| Nesting depth stays below threshold (default: 4 levels)      | [P/F/N/A]   | |
| Single Responsibility -- each function/class does one thing  | [P/F/N/A]   | |
| No dead code (unreachable branches, unused functions)        | [P/F/N/A]   | |

## Formatting

| Item                                                         | Result      | Notes        |
|--------------------------------------------------------------|-------------|--------------|
| Code passes the project linter/formatter with no violations  | [P/F/N/A]   | |
| Indentation is consistent (tabs vs. spaces per project config)| [P/F/N/A]  | |
| Line length stays within project limit                       | [P/F/N/A]   | |
| Blank lines used consistently to separate logical blocks     | [P/F/N/A]   | |

## Import / Dependency Organization

| Item                                                         | Result      | Notes        |
|--------------------------------------------------------------|-------------|--------------|
| Imports are grouped and ordered per project convention        | [P/F/N/A]   | |
| No unused imports                                            | [P/F/N/A]   | |
| No circular dependencies introduced                         | [P/F/N/A]   | |

## Error Handling

| Item                                                         | Result      | Notes        |
|--------------------------------------------------------------|-------------|--------------|
| Errors are handled, not silently swallowed                   | [P/F/N/A]   | |
| Error handling follows project patterns (e.g., Result types, exceptions) | [P/F/N/A] | |
| Error messages are descriptive and actionable                | [P/F/N/A]   | |
| No bare catch-all exception handlers without justification   | [P/F/N/A]   | |

## Logging

| Item                                                         | Result      | Notes        |
|--------------------------------------------------------------|-------------|--------------|
| Log levels used appropriately (debug, info, warn, error)     | [P/F/N/A]   | |
| No sensitive data logged (passwords, tokens, PII)            | [P/F/N/A]   | |
| Log messages include sufficient context for debugging        | [P/F/N/A]   | |

## Documentation

| Item                                                         | Result      | Notes        |
|--------------------------------------------------------------|-------------|--------------|
| Public APIs have doc comments                                | [P/F/N/A]   | |
| Non-obvious business logic has inline comments               | [P/F/N/A]   | |
| Comments explain "why," not "what"                           | [P/F/N/A]   | |

## Type Annotations / Safety

| Item                                                         | Result      | Notes        |
|--------------------------------------------------------------|-------------|--------------|
| Type annotations present on function signatures              | [P/F/N/A]   | |
| No unsafe type casts without documented justification        | [P/F/N/A]   | |
| Null/nil/None handling is explicit, not implicit             | [P/F/N/A]   | |

---

## Summary

| Category                       | Pass | Fail | N/A |
|--------------------------------|------|------|-----|
| Naming Conventions             | [N]  | [N]  | [N] |
| Code Structure                 | [N]  | [N]  | [N] |
| Formatting                     | [N]  | [N]  | [N] |
| Import / Dependency Org        | [N]  | [N]  | [N] |
| Error Handling                 | [N]  | [N]  | [N] |
| Logging                        | [N]  | [N]  | [N] |
| Documentation                  | [N]  | [N]  | [N] |
| Type Annotations / Safety      | [N]  | [N]  | [N] |

---

## Definition of Done

- [ ] All checklist items evaluated (Pass, Fail, or N/A)
- [ ] Failed items have notes explaining the issue
- [ ] Summary counts are accurate
- [ ] Results shared with the PR author

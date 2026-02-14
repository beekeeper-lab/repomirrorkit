# Acceptance Criteria

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| **Date**      | [YYYY-MM-DD]                   |
| **Owner**     | [BA name or persona]           |
| **Story ID**  | [US-000 — the story these criteria belong to] |
| **Related**   | [Links to user story, epic, or test plan] |
| **Status**    | Draft / Reviewed / Approved    |

*Use this template when acceptance criteria are complex enough to warrant a standalone document. For simpler stories, embed criteria directly in the user story template.*

## Writing Guidance

*Good acceptance criteria are:*
- *Testable -- a reviewer can verify pass/fail without ambiguity*
- *Independent -- each criterion can be validated on its own*
- *Specific -- no vague terms like "fast," "user-friendly," or "works correctly"*
- *Complete -- together they cover the happy path, edge cases, and error cases*

## Criteria

### AC-1: [Short descriptive label]

- **Given** [precondition -- the starting state of the system or user]
- **When** [trigger -- the action the user or system performs]
- **Then** [outcome -- the observable, verifiable result]

### AC-2: [Short descriptive label]

- **Given** [precondition]
- **When** [trigger]
- **Then** [outcome]

### AC-3: [Edge case or error scenario label]

- **Given** [precondition that sets up an unusual or error state]
- **When** [action that triggers the edge case]
- **Then** [expected system behavior -- error message, fallback, or graceful handling]

### AC-4: [Boundary or limit label]

- **Given** [precondition at a boundary -- e.g., maximum input length, zero items]
- **When** [action performed at that boundary]
- **Then** [expected behavior at the boundary]

*Add or remove AC blocks as needed. Cover at minimum: one happy path, one error path, and one boundary condition.*

## Verification Checklist

- [ ] Each criterion follows the Given/When/Then structure
- [ ] No criterion uses vague or subjective language
- [ ] Happy path, error paths, and boundary conditions are covered
- [ ] Criteria are consistent with the parent story's scope
- [ ] QA has reviewed and confirmed criteria are testable

## Definition of Done

- [ ] All criteria reviewed and approved by story owner
- [ ] QA confirms each criterion maps to at least one test case
- [ ] No open questions or ambiguities remain

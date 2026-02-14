# /backlog-refinement Command

Claude Code slash command that turns raw ideas, feature descriptions, or broad vision text into one or more well-formed beans through an iterative dialogue with the Team Lead.

## Purpose

Provides a structured "front door" to the beans workflow. Instead of requiring users to already know how to decompose their ideas into well-scoped beans, this command accepts free-form text and guides the user through a conversational refinement process. The Team Lead analyzes the input, asks clarifying questions, and creates properly-formed beans once understanding is clear.

## Usage

```
/backlog-refinement <text>
```

- `text` -- Free-form description of what you want to build, fix, or improve. Can be a single sentence or multiple paragraphs. Can describe one feature or an entire vision.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Raw text | Positional argument or pasted content | Yes |
| Backlog | `ai/beans/_index.md` | Yes (to check for duplicates and assign IDs) |
| Bean template | `ai/beans/_bean-template.md` | Yes (for bean creation) |

## Process

1. **Receive input** -- Accept the user's free-form text. This could range from a single sentence ("add dark mode") to paragraphs describing a broad vision.
2. **Analyze the text** -- Identify distinct units of work, themes, features, or concerns. Look for natural boundaries where one unit of work ends and another begins.
3. **Present initial breakdown** -- Show the user a proposed list of beans with working titles and one-line descriptions. Indicate which ideas seem like single beans vs. which might need splitting further.
4. **Ask clarifying questions** -- For each proposed bean, ask about:
   - **Priority:** How important is this relative to other work? (High / Medium / Low)
   - **Scope boundaries:** What's in vs. out? Are there pieces to defer?
   - **Dependencies:** Does this depend on other beans or existing work?
   - **Missing context:** Is there anything the Team Lead needs to understand better?
   - **Acceptance criteria:** What does "done" look like for the user?
5. **Iterate** -- Refine the breakdown based on the user's answers. Merge beans that are too small, split beans that are too large, adjust priorities, add missing context. Repeat until the user agrees with the proposed set.
6. **Create beans** -- For each agreed-upon bean, use `/new-bean` to create it with complete fields:
   - Problem Statement (derived from the user's description)
   - Goal (what success looks like)
   - Scope (In Scope / Out of Scope)
   - Acceptance Criteria (concrete, testable checklist)
   - Priority and any noted dependencies
7. **Present summary** -- Display all created beans in a table: Bean ID, Title, Priority, and a note about any dependencies between them.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| New beans | `ai/beans/BEAN-NNN-<slug>/bean.md` | One or more beans created via `/new-bean` |
| Updated index | `ai/beans/_index.md` | All new beans added to the backlog |
| Summary | Console output | Table of created beans with IDs, titles, and priorities |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | `false` | Show proposed beans without creating them. Useful for previewing before committing to the backlog. |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `EmptyInput` | No text provided | Prompt the user to provide a description of what they want |
| `DuplicateBean` | Proposed bean closely matches an existing bean in the backlog | Warn the user and ask if they want to create it anyway or skip |
| `UserAbort` | User decides to cancel mid-refinement | No beans created, no changes made |

## Examples

**Broad vision input:**
```
/backlog-refinement I want to add parallel processing to the long-run
command. It should use tmux to spawn multiple windows, each running
its own Claude Code instance working on a separate bean. We'll need
feature branches, a merge captain to handle merging, and updated
push hooks so we don't accidentally push to main.
```
Team Lead analyzes, identifies 4 potential beans (parallel execution, feature branches, merge captain, push hooks), asks clarifying questions, and creates them.

**Specific feature input:**
```
/backlog-refinement Add a /backlog-refinement command that takes
free-form text and turns it into beans through dialogue.
```
Team Lead identifies a single bean, asks about priority and acceptance criteria, creates one bean.

**Dry run:**
```
/backlog-refinement --dry-run We need user authentication, a dashboard,
and an API for mobile clients.
```
Shows proposed beans (auth, dashboard, mobile API) without creating them.

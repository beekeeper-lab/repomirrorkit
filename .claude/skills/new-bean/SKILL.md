# Skill: New Bean

## Description

Creates a new bean in the project's beans backlog. Assigns the next sequential ID, creates the bean directory with a `tasks/` subdirectory, populates `bean.md` from the project's bean template, and appends an entry to the backlog index. This is the standard way to add work items to the beans workflow.

## Trigger

- Invoked by the `/new-bean` slash command.
- Called by the Team Lead when new work is identified.
- Can be invoked by any persona who identifies work that needs a bean.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| title | Text | Yes | Short descriptive title for the bean |
| priority | Enum: `Low`, `Medium`, `High` | No | Defaults to `Medium` |
| problem_statement | Text | No | Description of the problem; can be filled in later |

## Process

1. **Read the backlog index (fresh)** -- Open `ai/beans/_index.md` **right now**, even if you read it recently. In a multi-agent environment, another agent may have added beans since your last read. Parse the Backlog table to find all existing bean IDs. Extract the highest BEAN-NNN number.

2. **Compute next ID** -- New ID = highest existing number + 1. Format as three-digit zero-padded: `BEAN-006`, `BEAN-007`, etc. **Never pre-assign IDs** — always derive the ID from the current state of `_index.md` at creation time.

3. **Generate slug** -- Convert the title to kebab-case:
   - Lowercase all characters
   - Replace spaces with hyphens
   - Strip non-alphanumeric characters (except hyphens)
   - Collapse multiple hyphens to one
   - Truncate to 50 characters maximum

4. **Check for duplicates** -- Verify no existing directory matches `ai/beans/BEAN-{NNN}-{slug}/`. If a collision exists, error with `DuplicateSlug`.

5. **Create directory structure** -- Create:
   - `ai/beans/BEAN-{NNN}-{slug}/`
   - `ai/beans/BEAN-{NNN}-{slug}/tasks/`

6. **Populate bean.md** -- Read `ai/beans/_bean-template.md`. Replace placeholders:
   - `BEAN-NNN` → the assigned ID
   - `[Title]` → the provided title
   - Status → `Unapproved`
   - Priority → from input or `Medium`
   - Created → today's date in `YYYY-MM-DD` format
   - Owner → `(unassigned)`
   - Problem Statement → from input or placeholder text
   Write the result to `ai/beans/BEAN-{NNN}-{slug}/bean.md`.

7. **Update backlog index** -- Append a new row to the Backlog table in `ai/beans/_index.md`:
   ```
   | BEAN-{NNN} | {title} | {priority} | Unapproved | — |
   ```

8. **Confirm** -- Report: bean ID, directory path, and remind the user to fill in Problem Statement, Goal, Scope, and Acceptance Criteria if not provided.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| bean_directory | Directory | `ai/beans/BEAN-{NNN}-{slug}/` with `tasks/` subdirectory |
| bean_spec | Markdown file | `ai/beans/BEAN-{NNN}-{slug}/bean.md` populated from template |
| updated_index | Markdown file | `ai/beans/_index.md` with new row appended |
| confirmation | Text | Bean ID and directory path |

## Quality Criteria

- Bean ID is unique and sequential (no gaps, no duplicates).
- Slug is valid kebab-case and readable.
- `bean.md` matches the template format with all metadata fields populated.
- The backlog index row is properly aligned with the existing table.
- The `tasks/` subdirectory exists and is empty (ready for Team Lead decomposition).

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoTitleProvided` | Title text is empty | Provide a descriptive title |
| `IndexNotFound` | `ai/beans/_index.md` does not exist | Create the beans directory structure first |
| `TemplateNotFound` | `ai/beans/_bean-template.md` does not exist | Create the bean template |
| `DuplicateSlug` | Directory already exists for this slug | Use a more specific title |

## Dependencies

- Bean template file at `ai/beans/_bean-template.md`
- Backlog index file at `ai/beans/_index.md`

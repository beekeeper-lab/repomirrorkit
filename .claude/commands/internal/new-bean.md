# /new-bean Command

Claude Code slash command that creates a new bean (work item) in the beans backlog with the correct ID, directory structure, and index entry.

## Purpose

Automates the boilerplate of creating a new bean: assigning the next sequential ID, creating the directory with `tasks/` subdirectory, populating `bean.md` from the template, and appending the entry to `_index.md`. This eliminates manual copy-paste errors and ensures every bean follows the standard format.

## Usage

```
/new-bean "<title>" [--priority <level>]
```

- `title` -- Short descriptive title for the bean (quoted string).

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Title | Positional argument (quoted) | Yes |
| Priority | `--priority` flag | No (defaults to `Medium`) |
| Problem statement | Interactive prompt | No (can be added later) |

## Process

1. **Scan for next ID** -- Read `ai/beans/_index.md` to find the highest existing BEAN-NNN number. The new bean gets NNN+1.
2. **Generate slug** -- Convert the title to kebab-case (lowercase, spaces to hyphens, strip special characters).
3. **Create directory** -- Create `ai/beans/BEAN-{NNN}-{slug}/` and `ai/beans/BEAN-{NNN}-{slug}/tasks/`.
4. **Populate bean.md** -- Copy the template from `ai/beans/_bean-template.md` and fill in:
   - Bean ID: `BEAN-{NNN}`
   - Status: `Unapproved`
   - Priority: from `--priority` flag or `Medium`
   - Created: today's date (YYYY-MM-DD)
   - Owner: `(unassigned)`
   - Title in the heading
5. **Update index** -- Append a row to the Backlog table in `ai/beans/_index.md` with the new bean's ID, title, priority, status `Unapproved`, and owner `—`.
6. **Confirm** -- Display the bean ID, directory path, and a reminder to fill in the Problem Statement and Acceptance Criteria.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Bean directory | `ai/beans/BEAN-{NNN}-{slug}/` | Bean directory with `tasks/` subdirectory |
| Bean spec | `ai/beans/BEAN-{NNN}-{slug}/bean.md` | Bean definition from template |
| Updated index | `ai/beans/_index.md` | New row in backlog table |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--priority <level>` | `Medium` | Priority: `Low`, `Medium`, `High` |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoTitleProvided` | Title is empty | Provide a descriptive title for the bean |
| `IndexNotFound` | `ai/beans/_index.md` does not exist | Run project scaffolding first or create the beans directory manually |
| `TemplateNotFound` | `ai/beans/_bean-template.md` does not exist | Create the bean template file |
| `DuplicateSlug` | A bean directory with the same slug already exists | Use a more specific title |

## Examples

**Simple bean:**
```
/new-bean "Add dark mode support"
```
Creates `ai/beans/BEAN-006-add-dark-mode-support/bean.md`, updates index.

**High-priority bean:**
```
/new-bean "Fix crash on startup with empty config" --priority High
```
Creates `ai/beans/BEAN-006-fix-crash-on-startup-with-empty-config/bean.md` with High priority.

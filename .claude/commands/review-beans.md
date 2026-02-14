# /review-beans Command

Generates a filtered Map of Content (MOC) linking to beans by status, then opens Obsidian on the `ai/beans/` directory for review.

## Purpose

Provides a comfortable way to review, edit, and approve beans outside the terminal. The user edits bean files directly in Obsidian — including changing status from `Unapproved` to `Approved` — and the changes persist because they are editing the real files.

## Usage

```
/review-beans [--status <status>] [--category <cat>]
```

- `--status <status>` — Filter by status. Default: `unapproved`. Accepts: `unapproved`, `approved`, `in-progress`, `done`, `deferred`, `all`.
- `--category <cat>` — Filter by category: `App`, `Process`, `Infra`. Case-insensitive. Default: all categories.

## Process

1. **Read backlog** — Parse `ai/beans/_index.md` and apply filters.
2. **Read summaries** — For each matching bean, read the first sentence of the Goal section.
3. **Generate MOC** — Write `ai/beans/_review.md` with Obsidian wiki-links to each matching bean, including priority, category, and summary.
4. **Open Obsidian** — Launch Obsidian pointing at `ai/beans/` and the `_review.md` file.
5. **Fallback** — If Obsidian is not installed, print the MOC file path for manual opening.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| MOC file | `ai/beans/_review.md` | Filtered list of beans with Obsidian-compatible links |
| Obsidian | (launched) | Obsidian opened on the beans directory |

## Examples

**Review unapproved beans (default):**
```
/review-beans
```
Generates MOC of all `Unapproved` beans and opens Obsidian.

**Review all approved beans:**
```
/review-beans --status approved
```
Shows beans that are approved and ready for execution.

**Review unapproved App beans only:**
```
/review-beans --status unapproved --category App
```
Filters to only unapproved beans in the App category.

**Review everything:**
```
/review-beans --status all
```
Shows all beans regardless of status.

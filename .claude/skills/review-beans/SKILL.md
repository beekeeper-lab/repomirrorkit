# Skill: Review Beans

## Description

Generates a filtered Map of Content (MOC) file linking to beans matching a given status and/or category, then opens Obsidian pointed at the `ai/beans/` directory. The user can review and edit bean files directly — including changing status from `Unapproved` to `Approved`. Edits happen in-place on real files.

## Trigger

- Invoked by the `/review-beans` slash command.
- Can be invoked by any persona or by the user directly.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| status | String | No | Filter beans by status. Default: `unapproved`. Accepts any valid status value. |
| category | String | No | Filter beans by category: `App`, `Process`, `Infra`. Case-insensitive. Default: show all categories. |

## Process

1. **Read the backlog index** — Parse `ai/beans/_index.md` to get all beans and their statuses, priorities, and categories.

2. **Apply filters** — Filter beans by the requested status (default: `unapproved`). If a category filter is provided, further filter to only matching categories. Case-insensitive matching.

3. **Read bean summaries** — For each matching bean, read the first sentence of the Goal section in its `bean.md` to use as a brief summary.

4. **Generate MOC file** — Write `ai/beans/_review.md` with:
   ```markdown
   # Bean Review

   **Filter:** Status = Unapproved | Category = All
   **Generated:** 2026-02-09 14:30

   ## Beans for Review (N total)

   | Bean | Priority | Category | Summary |
   |------|----------|----------|---------|
   | [[BEAN-072-obsidian-review-skill/bean\|BEAN-072]] | High | Process | Create /review-beans skill... |
   | [[BEAN-073-approval-gate-wiring/bean\|BEAN-073]] | High | Process | Wire approval gate lifecycle... |

   ## Quick Actions

   To approve a bean:
   1. Open the bean link above
   2. Change `| **Status** | Unapproved |` to `| **Status** | Approved |`
   3. Save the file
   4. Update the matching row in [[_index|_index.md]] with the new status

   To defer a bean:
   - Change status to `Deferred` in both `bean.md` and `_index.md`
   ```

   Use Obsidian wiki-link syntax (`[[path/to/file|Display Name]]`) so links are clickable in Obsidian.

5. **Detect Obsidian** — Check if Obsidian is available:
   - Try: `which obsidian` or check if the `obsidian` command exists
   - Try: check if the Obsidian URI scheme handler is registered (platform-dependent)

6. **Open Obsidian** — If Obsidian is detected:
   - Use the URI scheme: `xdg-open "obsidian://open?path=$(realpath ai/beans)&file=_review.md"` (Linux)
   - Or: `open "obsidian://open?path=$(realpath ai/beans)&file=_review.md"` (macOS)
   - If the URI scheme fails, fall back to: `obsidian ai/beans/`

7. **Report** — If Obsidian is not installed or the open command fails:
   - Print: "Obsidian not detected. The review file has been generated at: `ai/beans/_review.md`"
   - Print: "Open it manually in Obsidian or any markdown editor."
   - Still succeed — the MOC file is the primary output.

8. **Summary** — Report: number of beans matching the filter, path to the MOC file, and whether Obsidian was opened.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| moc_file | Markdown file | `ai/beans/_review.md` — filtered Map of Content with links to matching beans |
| obsidian_launch | Side effect | Obsidian opened targeting the beans directory (if available) |
| summary | Console text | Filter results, MOC path, Obsidian status |

## Quality Criteria

- The MOC file uses Obsidian-compatible wiki-links (`[[path|name]]`).
- All beans matching the filter are included — none are missed.
- The MOC includes enough context (priority, category, summary) for quick scanning.
- The "Quick Actions" section tells the user exactly how to approve or defer.
- Obsidian failure is graceful — the skill succeeds even if Obsidian is not installed.
- The MOC file is overwritten on each invocation (not appended to).

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoMatchingBeans` | No beans match the filter | Report "No beans with status [x] found." Suggest trying a different filter. |
| `IndexNotFound` | `ai/beans/_index.md` does not exist | No beans backlog — create it first |
| `ObsidianNotFound` | Obsidian is not installed | Graceful fallback — print the MOC path for manual opening |

## Dependencies

- Backlog index at `ai/beans/_index.md`
- Individual bean files at `ai/beans/BEAN-NNN-<slug>/bean.md`
- Obsidian (optional — graceful fallback if not installed)

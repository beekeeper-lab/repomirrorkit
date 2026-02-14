# /show-backlog Command

Displays the bean backlog in a concise table format showing each bean's ID, a one-sentence summary, and category.

## Usage

```
/show-backlog [--status <status>] [--category <cat>]
```

- `--status <status>` -- Filter by status: `Unapproved`, `Approved`, `In Progress`, `Done`, `Deferred`, or `open` (shortcut for all non-Done). Default: show all.
- `--category <cat>` -- Filter by category: `App`, `Process`, `Infra`. Case-insensitive. Default: show all.

## Process

1. **Read backlog** — Parse `ai/beans/_index.md` to get all beans.
2. **Apply filters** — If `--status` or `--category` is provided, filter the list.
3. **Read summaries** — For each bean, read the first sentence of the Goal section in its `bean.md` to use as the summary.
4. **Display table** — Output a markdown table:

```
| Bean | Summary | Category |
|------|---------|----------|
| BEAN-015 | Add --category flag to /long-run for filtering beans by type | Process |
| BEAN-013 | Create /deploy command for promoting test to main with quality gate | Infra |
```

5. **Show counts** — Below the table, show: `N total, N done, N open`

## Examples

**Show everything:**
```
/show-backlog
```

**Show only open (non-Done) beans:**
```
/show-backlog --status open
```

**Show only App beans:**
```
/show-backlog --category App
```

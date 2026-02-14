# Skill: Telemetry Report

## Description

Parses telemetry data from all bean.md files and produces an aggregate summary of project metrics: total time invested, average bean duration, breakdowns by category and owner, and identification of outliers.

## Trigger

- Invoked by the `/telemetry-report` slash command.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| category | String | No | Filter to a single category: `App`, `Process`, or `Infra`. Case-insensitive. |
| status | String | No | Filter by bean status. Default: `Done` (only completed beans). Use `all` for everything. |
| since | String | No | Only include beans created on or after this date (`YYYY-MM-DD`). |

## Process

1. **Read the backlog index** — Parse `ai/beans/_index.md` to get the list of all beans with their metadata (ID, title, category, status, owner).

2. **Apply filters** — If `category`, `status`, or `since` is provided, filter the bean list accordingly.

3. **Read telemetry from each bean** — For each bean in the filtered list, read its `bean.md` and extract:
   - The `Duration` field from the metadata table (e.g., `3m`, `1h 15m`, `< 1m`)
   - The `Started` and `Completed` fields
   - The `Category` and `Owner` fields
   - Parse duration strings to seconds for computation. Map: `< 1m` → 30s, `Xm` → X×60s, `Xh Ym` → (X×3600 + Y×60)s, `Xh` → X×3600s.

4. **Compute aggregate statistics:**
   - Total beans counted, beans with duration data, beans without
   - Total duration (sum of all bean durations)
   - Average duration per bean
   - Median duration
   - Standard deviation (if useful)

5. **Compute category breakdown:**

   ```
   | Category | Beans | Total Time | Avg Time |
   |----------|-------|------------|----------|
   | App      | 80    | 18h 30m    | 13m      |
   | Process  | 20    | 3h 10m     | 9m       |
   | Infra    | 10    | 1h 28m     | 8m       |
   ```

6. **Compute owner breakdown:**

   ```
   | Owner     | Beans | Total Time | Avg Time |
   |-----------|-------|------------|----------|
   | team-lead | 95    | 20h 5m     | 12m      |
   | developer | 15    | 3h 3m      | 12m      |
   ```

7. **Identify outliers:**
   - Top 5 longest beans (with ID, title, duration)
   - Top 5 shortest beans (with ID, title, duration)

8. **Display the report:**

   ```
   ===================================================
   TELEMETRY REPORT
   ===================================================
   Beans:    N total (N with data, N without)
   Time:     Xh Ym total
   Average:  Xm per bean
   Median:   Xm per bean
   ===================================================

   BY CATEGORY
   | Category | Beans | Total Time | Avg Time |
   ...

   BY OWNER
   | Owner | Beans | Total Time | Avg Time |
   ...

   LONGEST BEANS
   | Bean | Title | Duration |
   ...

   SHORTEST BEANS
   | Bean | Title | Duration |
   ...
   ===================================================
   ```

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| report | Console text | Formatted telemetry summary displayed in the terminal |

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| No beans found | Backlog is empty or filters match nothing | Report "No beans match the given filters" |
| No telemetry data | Beans exist but none have duration values | Report count and suggest running BEAN-114 backfill |

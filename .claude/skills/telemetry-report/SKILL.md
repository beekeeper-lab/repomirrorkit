# Skill: Telemetry Report

## Description

Parses telemetry data from all bean.md files and produces an aggregate summary of project metrics: total time invested, token usage, estimated dollar cost, breakdowns by category and owner, and identification of outliers.

## Trigger

- Invoked by the `/telemetry-report` slash command.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| category | String | No | Filter to a single category: `App`, `Process`, or `Infra`. Case-insensitive. |
| status | String | No | Filter by bean status. Default: `Done` (only completed beans). Use `all` for everything. |
| since | String | No | Only include beans created on or after this date (`YYYY-MM-DD`). |

## Process

1. **Read token pricing** — Parse `ai/context/token-pricing.md` to extract the input and output cost-per-token rates. Look for the table rows with `**Input Rate**` and `**Output Rate**`. Extract the dollar-per-token value (e.g., `$0.000015`). If the file is missing or unparseable, use fallback rates of $0.000015/input and $0.000075/output and note "⚠ Using fallback pricing" in the report.

2. **Read the backlog index** — Parse `ai/beans/_index.md` to get the list of all beans with their metadata (ID, title, category, status, owner).

3. **Apply filters** — If `category`, `status`, or `since` is provided, filter the bean list accordingly.

4. **Read telemetry from each bean** — For each bean in the filtered list, read its `bean.md` and extract:
   - The `Duration` field from the metadata table (e.g., `3m`, `1h 15m`, `< 1m`)
   - The `Started` and `Completed` fields
   - The `Category` and `Owner` fields
   - The per-task telemetry table: Duration, Tokens In, Tokens Out, Cost for each task
   - The summary table: Total Tasks, Total Duration, Total Tokens In, Total Tokens Out, Total Cost
   - Parse duration strings to seconds for computation. Map: `< 1m` → 30s, `Xm` → X×60s, `Xh Ym` → (X×3600 + Y×60)s, `Xh` → X×3600s.

5. **Compute cost per bean** — For each bean:
   - If `Total Cost` is already populated in bean.md, use that value.
   - Otherwise, compute from token totals: `cost = (total_tokens_in × input_rate) + (total_tokens_out × output_rate)`
   - Format: `$X.XX` (two decimal places). Use `< $0.01` for amounts under one cent.

6. **Compute aggregate statistics:**
   - Total beans counted, beans with duration data, beans without
   - Total duration (sum of all bean durations)
   - Average duration per bean
   - Median duration
   - Total tokens (in + out across all beans)
   - **Total cost** (sum of all bean costs)
   - **Average cost per bean**

7. **Compute category breakdown:**

   ```
   | Category | Beans | Total Time | Avg Time | Total Cost | Avg Cost |
   |----------|-------|------------|----------|------------|----------|
   | App      | 80    | 18h 30m    | 13m      | $142.50    | $1.78    |
   | Process  | 20    | 3h 10m     | 9m       | $28.30     | $1.42    |
   | Infra    | 10    | 1h 28m     | 8m       | $12.10     | $1.21    |
   ```

8. **Compute owner breakdown:**

   ```
   | Owner     | Beans | Total Time | Avg Time | Total Cost | Avg Cost |
   |-----------|-------|------------|----------|------------|----------|
   | team-lead | 95    | 20h 5m     | 12m      | $155.00    | $1.63    |
   | developer | 15    | 3h 3m      | 12m      | $27.90     | $1.86    |
   ```

9. **Identify outliers:**
   - Top 5 most expensive beans (with ID, title, cost)
   - Top 5 longest beans (with ID, title, duration)
   - Top 5 cheapest beans with data (with ID, title, cost)

10. **Display the report:**

    ```
    ===================================================
    TELEMETRY REPORT
    ===================================================
    Pricing:  Claude Opus 4 — $15/MTok in, $75/MTok out
              (from ai/context/token-pricing.md)
    Beans:    N total (N with data, N without)
    Time:     Xh Ym total
    Average:  Xm per bean
    Median:   Xm per bean
    Cost:     $XXX.XX total ($X.XX avg per bean)
    ===================================================

    BY CATEGORY
    | Category | Beans | Total Time | Avg Time | Total Cost | Avg Cost |
    ...

    BY OWNER
    | Owner | Beans | Total Time | Avg Time | Total Cost | Avg Cost |
    ...

    MOST EXPENSIVE BEANS
    | Bean | Title | Cost | Tokens |
    ...

    LONGEST BEANS
    | Bean | Title | Duration |
    ...

    CHEAPEST BEANS (with data)
    | Bean | Title | Cost | Tokens |
    ...
    ===================================================
    ```

**Single-bean mode** — When a specific bean ID is provided as an argument, show detailed telemetry for just that bean including the per-task breakdown with cost:

    ```
    TASK BREAKDOWN
    | # | Task | Owner | Duration | Tokens In | Tokens Out | Cost |
    ...

    SUMMARY
    | Metric | Value |
    | Total Cost | $X.XX |
    ...
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
| Pricing file missing | `ai/context/token-pricing.md` not found | Use fallback rates and warn in report header |

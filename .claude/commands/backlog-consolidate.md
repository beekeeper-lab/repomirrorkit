# /backlog-consolidate Command

Claude Code slash command that detects and resolves duplicates, overlaps, contradictions, missing dependencies, and merge opportunities across recently created beans. Designed for post-refinement cleanup after running multiple `/backlog-refinement` sessions in parallel.

## Purpose

When multiple refinement sessions run in parallel (e.g., 3 Claude windows creating 5-7 beans each), the resulting 15-20 new beans inevitably contain duplicates, overlapping scope, contradictions, and dependency gaps. This command automates the detection of these issues and provides an iterative dialogue to clean up the backlog.

## Usage

```
/backlog-consolidate [--status <status>] [--dry-run]
```

- `--status <value>` — Filter which beans to analyze. Default: `Unapproved`. Also accepts `open` (Unapproved + Approved + In Progress), `all`, or any single status value.
- `--dry-run` — Show findings and proposed changes without applying them.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Backlog | `ai/beans/_index.md` | Yes (to identify target beans and reference set) |
| Bean files | `ai/beans/BEAN-NNN-<slug>/bean.md` | Yes (full content of each target bean) |
| Done beans | Same path, filtered to Done status | Yes (to detect duplication of completed work) |

## Process

1. **Read the backlog** — Parse `ai/beans/_index.md`, filter to target beans (default: `Unapproved`). Also load all Done beans as a reference set.
2. **Load all target bean files** — Read each `bean.md` in full: Problem Statement, Goal, Scope, Acceptance Criteria, Notes.
3. **Run analysis checks** — Compare every pair of target beans plus each target bean against Done beans. Detect:
   - **Duplicates** — Near-identical Problem Statements or Goals (Critical)
   - **Scope Overlaps** — Both beans list the same files, modules, or features (High)
   - **Contradictions** — Acceptance criteria that conflict (Critical)
   - **Missing Dependencies** — Bean A modifies something Bean B reads (High)
   - **Merge Candidates** — Small beans touching the same area (Medium)
   - **Done Duplication** — New bean's goal matches an already-Done bean (High)
   - **Dependency Cycles** — A depends on B depends on A (High)
   - **Priority Inconsistencies** — High bean depends on unscheduled Low bean (Medium)
4. **Present findings** — Grouped by severity (Critical, High, Medium) with specific evidence quoted from bean files.
5. **Iterate with user** — For each finding, ask what to do: merge, delete, add dependency, rewrite scope, or ignore.
6. **Apply agreed changes** — Re-read `_index.md` before each write. Merge beans, delete beans, add dependencies, rewrite scope, fix cross-references.
7. **Present summary** — Show a change log: how many beans merged, deleted, dependencies added, scopes rewritten, and the final bean count.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Modified beans | `ai/beans/BEAN-NNN-<slug>/bean.md` | Beans with updated scope, dependencies, or merged content |
| Deleted beans | (removed) | Bean directories removed for duplicates |
| Updated index | `ai/beans/_index.md` | Reflects merges, deletions, and status changes |
| Summary | Console output | Change log with counts and final bean total |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--status <value>` | `Unapproved` | Filter beans to analyze. `open` = Unapproved + Approved + In Progress. `all` = every status. |
| `--dry-run` | `false` | Show findings and proposed changes without applying them. |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoTargetBeans` | No beans match the status filter | Tell user — nothing to consolidate |
| `SingleBean` | Only one bean matches — nothing to compare | Tell user — need at least 2 beans to consolidate |
| `ConcurrentEdit` | Another agent modified a bean during execution | Abort current operation, re-read, report conflict |
| `UserAbort` | User decides to cancel mid-consolidation | No changes applied |

## Examples

**After a parallel refinement session:**
```
/backlog-consolidate
```
Analyzes all Unapproved beans, finds duplicates and overlaps, presents findings, and applies agreed changes.

**Dry run to preview issues:**
```
/backlog-consolidate --dry-run
```
Shows all findings without modifying any files.

**Analyze all open beans:**
```
/backlog-consolidate --status open
```
Includes Unapproved, Approved, and In Progress beans in the analysis.

**Analyze the entire backlog:**
```
/backlog-consolidate --status all
```
Checks every bean regardless of status, including cross-status dependency issues.

# /seed-tasks Command

Claude Code slash command that generates an initial set of tasks from project objectives and assigns them to team personas.

## Purpose

Bootstrap a project's task backlog by decomposing high-level objectives into discrete, assignable tasks. Each task is mapped to the most appropriate persona, given a priority, and linked to its dependencies. The output is a set of task files and a dependency graph that the Team Lead can immediately begin executing against.

## Usage

```
/seed-tasks [objectives-file]
```

- `objectives-file` -- Path to a markdown or YAML file listing project objectives. Defaults to `./ai/objectives.md` if omitted.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Project objectives | Objectives file (markdown or YAML) | Yes |
| Team composition | `composition.yml` or compiled `CLAUDE.md` | Yes |
| Task taxonomy | `workflows/task-taxonomy.md` in the library | No (uses defaults if absent) |
| Task spec template | `personas/team-lead/templates/task-spec.md` | No (uses built-in format if absent) |

The objectives file should contain numbered or bulleted objectives, each with enough context to determine scope. Objectives can optionally include priority hints and acceptance criteria.

## Process

1. **Parse project objectives** -- Read the objectives file and extract each discrete objective. Identify any explicit priority, scope, or constraint annotations.
2. **Load team composition** -- Determine which personas are available for assignment by reading the composition spec or compiled CLAUDE.md.
3. **Map objectives to task categories** -- Using the task taxonomy (from `workflows/task-taxonomy.md`), classify each objective into one or more task categories: architecture, implementation, testing, documentation, security review, compliance check, design, research, integration, or release.
4. **Decompose into tasks** -- Break each objective into one or more concrete tasks. Each task gets:
   - A clear title and description
   - A primary persona assignment based on task category
   - Acceptance criteria derived from the objective
   - An estimated complexity (small, medium, large)
5. **Assign dependencies and priority** -- Analyze the task set for ordering constraints. Architecture tasks precede implementation; implementation precedes testing; security review runs in parallel with QA. Assign a priority (P0 critical, P1 high, P2 standard, P3 low) based on objective priority and dependency position.
6. **Generate task files** -- Write each task as a markdown file using the task spec template from `personas/team-lead/templates/task-spec.md`. Files are named with a numeric prefix for ordering.
7. **Produce dependency graph** -- Generate a summary file showing task dependencies as a directed list, making the execution order visible at a glance.
8. **Produce assignment summary** -- Generate a summary grouped by persona, showing each persona's assigned tasks and total estimated load.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Task files | `{project}/ai/tasks/NNN-{slug}.md` | One file per task, using the task spec template |
| Dependency graph | `{project}/ai/tasks/dependency-graph.md` | Directed dependency list across all tasks |
| Assignment summary | `{project}/ai/tasks/assignment-summary.md` | Tasks grouped by persona with load estimates |
| Seeding plan | `{project}/ai/tasks/seeding-plan.md` | Overview document using `task-seeding-plan.md` template |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--max-tasks <n>` | No limit | Cap the total number of generated tasks |
| `--cycle-scope <label>` | `cycle-1` | Label for the current work cycle; tasks are scoped to this cycle |
| `--format <md\|yaml>` | `md` | Output format for task files |
| `--persona-filter <ids>` | All personas | Only generate tasks for specific personas (comma-separated) |
| `--dry-run` | `false` | Show what tasks would be generated without writing files |
| `--verbose` | `false` | Print decomposition reasoning for each objective |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `ObjectivesFileNotFound` | The objectives file does not exist at the expected path | Provide the correct path or create `./ai/objectives.md` |
| `NoObjectivesParsed` | The file was found but no objectives could be extracted | Ensure objectives are listed as numbered or bulleted items |
| `NoTeamComposition` | Neither `composition.yml` nor compiled `CLAUDE.md` found | Run `/compile-team` first or provide a composition file |
| `UnassignableTask` | A task category does not map to any persona in the team | Add the missing persona to the composition or manually assign the task |
| `TaxonomyParseError` | The task taxonomy file is malformed | Check `workflows/task-taxonomy.md` for formatting issues |

## Examples

**Seed tasks from default objectives file:**
```
/seed-tasks
```
Reads `./ai/objectives.md`, decomposes objectives into tasks, assigns personas, and writes task files to `./ai/tasks/`.

**Seed from a specific objectives file with a task cap:**
```
/seed-tasks ./docs/sprint-3-objectives.md --max-tasks 20 --cycle-scope sprint-3
```
Generates at most 20 tasks scoped to sprint-3 from the given objectives file.

**Preview task decomposition without writing:**
```
/seed-tasks --dry-run --verbose
```
Shows the full decomposition reasoning and lists all tasks that would be created, their persona assignments, and dependencies -- without writing any files.

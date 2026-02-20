# Skill: Seed Tasks

## Description

Decomposes project objectives into actionable, assignable tasks. Each generated
task is scoped to a single work cycle, assigned to exactly one primary persona,
given testable acceptance criteria, and linked to its dependencies. This skill
bridges the gap between high-level goals and the concrete work items that
personas execute. It runs during the Seed phase of the Foundry pipeline
(Select --> Compose --> Compile --> Scaffold --> **Seed** --> Export).

## Trigger

- Invoked by the `/seed-tasks` slash command.
- Called programmatically by `foundry_app/services/seeder.py` at project kickoff or cycle start.
- Can be re-run mid-project when objectives change or new work is identified.

## Inputs

| Input               | Type                  | Required | Description                                                          |
|---------------------|-----------------------|----------|----------------------------------------------------------------------|
| project_objectives  | Text or file path     | Yes      | What the project aims to achieve; one or more goal statements        |
| team_composition    | YAML file path        | Yes      | Which personas are active and available for assignment                |
| task_taxonomy       | File path             | No       | Classification reference; defaults to `workflows/task-taxonomy.md`   |
| max_tasks_per_cycle | Integer               | No       | Cap on tasks generated per cycle; defaults to no limit               |

## Process

1. **Parse project objectives into discrete goals** -- Split compound objectives into independent, measurable goal statements. Each goal should be verifiable on its own.
2. **Map each goal to task categories** -- Using the task taxonomy, classify each goal (e.g., design, implementation, testing, documentation, infrastructure).
3. **Decompose goals into implementable tasks** -- Break each goal into tasks that can be completed within a single work cycle. If a task is too large, split it further.
4. **Assign a primary persona per task** -- Use the category-to-persona mapping (e.g., implementation tasks go to `developer`, test tasks go to `tech-qa`, documentation tasks go to `technical-writer`).
5. **Identify dependencies between tasks** -- Mark blocking relationships (e.g., "implement API" blocks "write API tests"). Flag any circular dependencies as errors.
6. **Priority-rank tasks** -- Produce a strict ordering with no ties. Rank by dependency depth first (blockers before dependents), then by business value.
7. **Generate task files with acceptance criteria** -- Write one markdown file per task containing: title, description, assigned persona, acceptance criteria, dependencies, and priority rank. Include telemetry fields in the task file metadata table, initialized to `—`:
   - **Started:** —
   - **Completed:** —
   - **Duration:** —
   - **Tokens:** —

## Outputs

| Output              | Type                        | Description                                                    |
|---------------------|-----------------------------|----------------------------------------------------------------|
| task_files          | Directory of markdown files | One file per task, named `TASK-{NNN}-{slug}.md`                |
| dependency_graph    | Text (Mermaid)              | Visual dependency map suitable for rendering in markdown       |
| assignment_summary  | Markdown table              | Persona-to-task-count mapping showing workload distribution    |

## Quality Criteria

- Every generated task has exactly one assigned persona from the active team composition.
- Every task has at least one testable acceptance criterion (binary pass/fail, no subjective language).
- Every task explicitly declares its dependencies (or states "none").
- Every task is scoped to a single work cycle -- no multi-cycle epics disguised as tasks.
- The dependency graph is acyclic; circular dependencies are rejected.
- The priority ranking is a strict total order with no ties.
- If `max_tasks_per_cycle` is set, the output respects the cap.
- No persona is assigned zero tasks unless the objectives genuinely require no work from that role.

## Error Conditions

| Error                       | Cause                                                | Resolution                                                 |
|-----------------------------|------------------------------------------------------|------------------------------------------------------------|
| `EmptyObjectives`           | No project objectives provided or file is empty      | Supply at least one concrete objective                     |
| `NoActivePersonas`          | Team composition has zero active personas             | Check the composition YAML; at least one persona must be active |
| `TaxonomyNotFound`          | The task taxonomy file path does not exist            | Provide a valid path or ensure the default taxonomy is present |
| `CircularDependency`        | Two or more tasks form a dependency cycle             | Review the generated tasks and break the cycle manually    |
| `UnmappableGoal`            | A goal cannot be mapped to any task category          | Refine the objective or extend the task taxonomy           |
| `PersonaCapacityExceeded`   | One persona is assigned more tasks than cycle allows  | Increase `max_tasks_per_cycle` or split work across cycles |

## Dependencies

- **Compile Team** skill (team composition must be compiled before seeding)
- Access to `workflows/task-taxonomy.md` for category classification
- Active persona definitions from `personas/{name}/persona.md` for role-matching
- `foundry_app/services/seeder.py` -- reference implementation of the seed logic
- `foundry_app/core/models.py` -- CompositionSpec model for parsing team composition

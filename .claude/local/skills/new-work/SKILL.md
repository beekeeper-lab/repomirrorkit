# Skill: New Work

## Description

Single entry point for initiating any unit of work: bug fix, feature, chore,
spike, or refactor. Collects the work type, goal, constraints, urgency, and
affected areas, then creates a Task Spec, optionally drafts a BA artifact
(user story for features, bug report for bugs), and seeds initial tasks with
the appropriate dependency wave. This skill replaces the need for separate
bug/feature/chore commands by routing through one consistent funnel that
adapts its output based on the work type.

## Trigger

- Invoked by the `/new-work` slash command.
- Called by the Team Lead persona when new work enters the pipeline.
- Can be invoked by any persona who identifies work that needs to be done.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| type | Enum: `bug`, `feature`, `chore`, `spike`, `refactor` | Yes | The kind of work being created |
| goal | Text | Yes | What this work aims to accomplish — the desired end state |
| constraints | Text | No | Time, scope, or technical constraints (e.g., "must not break existing API") |
| urgency | Enum: `low`, `normal`, `high`, `critical` | No | Priority level; defaults to `normal` |
| affected_areas | List of strings | No | Components, modules, or subsystems involved |
| composition_spec | File path | No | Composition spec for team context; auto-detected from `ai/team/composition.yml` |
| seed | Boolean | No | Whether to seed tasks immediately; defaults to `true` |

## Process

1. **Assign work ID** -- Generate a sequential ID by scanning `ai/tasks/` for existing work directories. Format: `WRK-{NNN}` (e.g., `WRK-001`).
2. **Create work directory** -- Create `ai/tasks/{id}-{type}-{slug}/` where slug is a kebab-case summary of the goal.
3. **Generate Task Spec** -- Write `task.md` in the work directory containing:
   - Work ID, type, and slug
   - Goal statement
   - Constraints (if provided)
   - Urgency level
   - Affected areas
   - Status: `open`
   - Acceptance criteria (derived from the goal — what must be true for this work to be "done")
4. **Route by type** -- Based on the work type, produce additional artifacts:
   - **feature**: Draft a user story in `ai/outputs/ba/user-stories/` using the BA story template. Include acceptance criteria derived from the goal. Link the story to the task spec.
   - **bug**: Draft a bug report in `ai/outputs/ba/bug-reports/` using the BA bug-report template. Include reproduction steps (if known), expected vs actual behavior, and severity.
   - **chore**: No additional BA artifact. Task spec is sufficient.
   - **spike**: Create a spike summary template in the work directory with time-box, questions to answer, and success criteria.
   - **refactor**: Create a refactoring brief in the work directory with current state, target state, and risk assessment.
5. **Determine affected personas** -- Based on the work type and affected areas, identify which personas will be involved. Map to the standard dependency wave:
   - feature: BA → Architect → Developer → Tech-QA
   - bug: Developer → Tech-QA (skip BA/Architect for simple bugs; include them for complex ones)
   - chore: Developer (or DevOps, depending on area)
   - spike: Researcher or Architect → Developer
   - refactor: Architect → Developer → Tech-QA
6. **Seed initial tasks** -- If `seed` is true, call the Seed Tasks skill to create the first wave of tasks for the affected personas, scoped to this work item. Tasks reference the work ID.
7. **Update shared task list** -- If a shared task list exists (`ai/tasks/seeded-tasks.md` or equivalent), append the new work item with its tasks.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| task_spec | Markdown file | `ai/tasks/{id}-{type}-{slug}/task.md` — the authoritative work definition |
| ba_artifact | Markdown file | User story or bug report (for feature/bug types only) |
| seeded_tasks | Markdown files | Initial tasks for affected personas (if seed=true) |
| work_summary | Text | Confirmation with work ID, type, assigned personas, and created files |

## Quality Criteria

- The work ID is unique and sequential across all work items in the project.
- The task spec is self-contained: a persona unfamiliar with the context can understand what needs to be done.
- Acceptance criteria are testable — binary pass/fail, not subjective.
- The type-specific routing produces the correct artifact: features get stories, bugs get reports, spikes get time-boxed briefs.
- Seeded tasks respect the dependency wave appropriate for the work type.
- Urgency level propagates to seeded tasks so personas can prioritize correctly.
- The slug in the directory name is readable and unique within the project.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoGoalProvided` | Goal text is empty | Provide a clear goal statement |
| `InvalidType` | Work type is not one of the supported values | Use: bug, feature, chore, spike, or refactor |
| `TasksDirNotWritable` | Cannot write to `ai/tasks/` | Check permissions or ensure the project is scaffolded |
| `NoActivePersonas` | Composition has no personas for the selected work type | Add appropriate personas to the composition |
| `DuplicateSlug` | A work directory with the same slug already exists | Use a more specific goal or different slug |

## Dependencies

- **Scaffold Project** skill (project must be scaffolded before creating work)
- **Seed Tasks** skill (called when `seed=true`)
- BA persona's templates for story and bug report artifacts
- Composition spec for team context and persona availability

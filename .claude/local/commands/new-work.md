# /new-work Command

Claude Code slash command that creates a new work item — the single entry point for bugs, features, chores, spikes, and refactors.

## Purpose

One consistent funnel for all new work. Instead of separate commands for bugs, features, and chores, `/new-work` asks the right questions, creates a task spec, drafts the appropriate BA artifact (story or bug report), and seeds initial tasks. This ensures every piece of work gets the same structural treatment regardless of type.

## Usage

```
/new-work <type> "<goal>" [--urgency <level>] [--no-seed]
```

- `type` -- One of: `bug`, `feature`, `chore`, `spike`, `refactor`.
- `goal` -- What this work aims to accomplish (quoted string).

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Work type | Positional argument | Yes |
| Goal | Positional argument (quoted) | Yes |
| Urgency | `--urgency` flag | No (defaults to `normal`) |
| Constraints | `--constraints` flag or interactive prompt | No |
| Affected areas | `--areas` flag | No |
| Composition | Auto-detected from `ai/team/composition.yml` | No |

## Process

1. **Assign ID** -- Auto-increment from existing work items in `ai/tasks/`.
2. **Create task spec** -- Write the work definition with goal, constraints, urgency, and acceptance criteria.
3. **Route by type** -- Draft a user story (feature), bug report (bug), spike brief (spike), refactoring brief (refactor), or nothing extra (chore).
4. **Seed tasks** -- Create initial tasks for the appropriate persona wave (unless `--no-seed`).
5. **Confirm** -- Display the work ID, created files, and assigned personas.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Task spec | `ai/tasks/{id}-{type}-{slug}/task.md` | Authoritative work definition |
| BA artifact | `ai/outputs/ba/user-stories/` or `ai/outputs/ba/bug-reports/` | Story or bug report (feature/bug only) |
| Seeded tasks | `ai/tasks/` | Initial tasks for affected personas |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--urgency <level>` | `normal` | Priority: `low`, `normal`, `high`, `critical` |
| `--constraints <text>` | None | Time, scope, or technical constraints |
| `--areas <list>` | None | Comma-separated affected components or modules |
| `--no-seed` | `false` | Create the task spec without seeding tasks |
| `--assign <persona>` | Auto-detected | Override the initial persona assignment |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoGoalProvided` | Goal is empty | Provide a goal describing the desired outcome |
| `InvalidType` | Type is not bug/feature/chore/spike/refactor | Use a supported work type |
| `TasksDirNotWritable` | Cannot write to `ai/tasks/` | Scaffold the project first |

## Examples

**New feature:**
```
/new-work feature "Add user authentication with OAuth2"
```
Creates task spec, drafts a user story, seeds tasks for BA → Architect → Developer → Tech-QA.

**Critical bug:**
```
/new-work bug "Login fails when email contains a plus sign" --urgency critical
```
Creates task spec with critical urgency, drafts a bug report, seeds tasks for Developer → Tech-QA.

**Chore with constraints:**
```
/new-work chore "Upgrade Python from 3.11 to 3.12" --constraints "Must not break CI pipeline" --areas build,ci
```
Creates task spec only (no BA artifact), seeds tasks for Developer → DevOps.

**Spike without seeding:**
```
/new-work spike "Evaluate GraphQL vs REST for the public API" --no-seed
```
Creates a time-boxed spike brief. No tasks seeded — the investigator decides next steps after the spike.

**Refactor:**
```
/new-work refactor "Extract authentication logic into a shared middleware" --areas auth,api
```
Creates task spec with current-state/target-state brief, seeds tasks for Architect → Developer → Tech-QA.

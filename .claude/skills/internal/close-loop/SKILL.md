# Skill: Close Loop

## Description

Verifies task completion by checking produced artifacts against the original
acceptance criteria, runs quality checks, and closes the feedback loop between
requesting and producing personas. If all criteria pass, the task is marked
complete and downstream consumers are notified. If criteria fail, the task is
returned to the producer with specific, actionable failure reasons. This skill
enforces the quality contract that keeps the autonomous team reliable.

## Trigger

- Invoked automatically when a persona marks a task as complete.
- Invoked by the `/close-loop` slash command for on-demand status verification.
- Called programmatically by the orchestration layer after artifact production.

## Inputs

| Input              | Type        | Required | Description                                                              |
|--------------------|-------------|----------|--------------------------------------------------------------------------|
| task_id            | String      | Yes      | Identifier of the task being verified (e.g., `TASK-007-implement-api`)   |
| task_spec          | File path   | Yes      | The original task specification containing acceptance criteria            |
| produced_artifacts | File list   | Yes      | Paths to every output artifact claimed by the producing persona          |
| persona_outputs_md | File path   | Yes      | The producing persona's `outputs.md` defining quality bar references     |

## Process

1. **Load the task specification and its acceptance criteria** -- Parse the task file, extract each acceptance criterion as a discrete checkable item.
2. **Inventory the produced artifacts** -- Confirm every claimed artifact exists on disk, is non-empty, and has the expected file type.
3. **Verify each acceptance criterion against the artifacts** -- Evaluate every criterion as pass, fail, or partial. Record evidence for each judgment.
4. **Check artifacts against the quality bar** -- Compare outputs to the standards defined in the producing persona's `outputs.md` (formatting, completeness, depth).
5. **Run automated quality checks** -- Execute any applicable automated validation: linting, test suites, format checks, schema validation. Record results.
6. **Generate a verification report** -- Produce a structured report listing each criterion, its status, and supporting evidence or failure reasons.
7. **If all criteria pass** -- Mark the task as `complete`. Identify downstream tasks that were blocked and notify the consuming persona(s) that the dependency is satisfied.
8. **Record task completion telemetry** -- After the task passes verification:
   - If the task file's `Started` field is `—` (unset), record it now as the current timestamp (`YYYY-MM-DD HH:MM`). This is a fallback — normally `Started` is set when task execution begins.
   - Record the `Completed` timestamp (`YYYY-MM-DD HH:MM`) in the task file metadata.
   - Compute `Duration`: the PostToolUse telemetry hook auto-computes duration from git timestamps (first commit on the feature branch → now) when the bean is marked Done. This gives second-level precision. If git data is unavailable, it falls back to `Started` → `Completed` metadata timestamps. Format: `< 1m`, `Xm`, or `Xh Ym`.
   - **Token counts**: Claude Code does not expose session token counts programmatically. Token fields should be left as `—`. If a future Claude Code update exposes `/cost` data, this can be revisited.
   - Update the bean's **Telemetry per-task table** (in `bean.md`): find the row matching the task number and fill in Task name, Owner, and Duration. Token columns remain `—`.
9. **If any criteria fail** -- Mark the task as `returned`. Send the verification report back to the producing persona with specific, actionable failure descriptions.

## Outputs

| Output                 | Type                                       | Description                                                       |
|------------------------|--------------------------------------------|-------------------------------------------------------------------|
| verification_report    | Markdown file                              | Detailed pass/fail/partial status per acceptance criterion        |
| task_status            | Enum: `complete`, `returned`, `blocked`    | Updated state of the task after verification                      |
| handoff_notification   | Text                                       | Message to downstream persona(s) if task is complete; includes artifact locations |

## Quality Criteria

- Every acceptance criterion from the task spec is explicitly evaluated -- none are skipped.
- Each criterion verdict includes evidence (file path, line reference, test output) rather than bare assertions.
- Partial verdicts explain exactly what is missing and what would move the criterion to pass.
- The verification report is actionable: a producer who receives a `returned` status can fix every issue without asking clarifying questions.
- Automated checks (lint, test, format) are run when applicable tooling is available; their absence is noted in the report.
- The handoff notification includes the exact artifact paths that downstream consumers need.
- Status transitions are idempotent: re-running close-loop on an already-complete task produces the same result.

## Error Conditions

| Error                      | Cause                                                 | Resolution                                                   |
|----------------------------|-------------------------------------------------------|--------------------------------------------------------------|
| `TaskNotFound`             | The task_id does not match any known task file         | Verify the task_id and ensure the task file exists           |
| `TaskSpecMissingCriteria`  | The task spec has no acceptance criteria defined       | Add at least one testable criterion to the task spec         |
| `ArtifactMissing`          | A claimed artifact path does not exist on disk         | Ensure the producing persona wrote all outputs to the correct paths |
| `ArtifactEmpty`            | An artifact file exists but is zero bytes              | Re-produce the artifact; empty files do not satisfy criteria |
| `PersonaOutputsNotFound`   | The persona's `outputs.md` file cannot be located      | Check the persona directory in the library for `outputs.md`  |
| `AutomatedCheckFailed`     | A linter, test suite, or formatter returned errors     | Fix the reported issues and re-submit the artifacts          |
| `DownstreamPersonaUnknown` | A dependent task references a persona not in the team  | Update the team composition or reassign the downstream task  |

## Dependencies

- **Seed Tasks** skill (tasks must exist before they can be closed)
- Access to the producing persona's `outputs.md` for quality bar definitions
- Access to the task file generated by the Seed Tasks skill
- Automated tooling (linters, test runners) when available in the project environment
- Dependency graph from Seed Tasks to identify downstream consumers for handoff

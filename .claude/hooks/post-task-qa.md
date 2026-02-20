# Hook Pack: Post-Task QA

## Purpose

Verifies that completed tasks actually meet their acceptance criteria and produce the required outputs. Prevents tasks from being marked "done" when deliverables are missing or incomplete.

## Hooks

| Hook Name | Trigger | Check | Pass Criteria | Fail Action |
|-----------|---------|-------|---------------|-------------|
| `output-exists` | `post-task-complete` | Verify all declared output files exist on disk | Every file listed in the task's outputs is present | Block task completion; list missing files |
| `acceptance-criteria-check` | `post-task-complete` | Verify acceptance criteria checkboxes are checked | All `- [x]` items marked complete | Block task completion; list unchecked items |
| `template-conformance` | `post-task-complete` | Compare output against its template for required sections | All required sections present and non-empty | Warn (advisory) or block; list missing sections |
| `downstream-notification` | `post-task-complete` | Notify dependent personas that a blocking input is ready | Notification recorded in manifest | Log only; never blocks |

## Configuration

- **Default mode:** enforcing (except `downstream-notification` which is always advisory)
- **Timeout:** 30 seconds per hook
- **Customization:** `template-conformance` can be set to advisory mode for exploratory tasks where rigid template adherence is counterproductive.

## Posture Compatibility

| Posture | Included | Default Mode |
|---------|----------|--------------|
| `baseline` | Yes | enforcing |
| `hardened` | Yes | enforcing |
| `regulated` | Yes | enforcing |

This pack is included at all posture levels to ensure task outputs are verifiable regardless of project type.

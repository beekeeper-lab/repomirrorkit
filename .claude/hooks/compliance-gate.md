# Hook Pack: Compliance Gate

## Category
code-quality

## Purpose

Enforces compliance requirements for regulated environments. Collects evidence, verifies controls, maintains audit trails, and ensures separation of duties. Required for projects handling sensitive data, financial systems, or healthcare information.

## Hooks

| Hook Name | Trigger | Check | Pass Criteria | Fail Action |
|-----------|---------|-------|---------------|-------------|
| `evidence-collection` | `post-task-complete` | Verify that required compliance evidence artifacts are attached to the task output | All required evidence files present and non-empty | Block task completion; list missing evidence |
| `control-verification` | `pre-release` | Check that all applicable controls from the project's control framework are satisfied | Every mapped control has a passing verification | Block release; list unsatisfied controls |
| `audit-trail` | `post-task-complete` | Record an immutable audit entry with persona, action, timestamp, and outcome | Audit entry successfully written | Block task completion; report write failure |
| `separation-of-duties` | `post-review` | Verify that the reviewer is not the same persona that authored the work | Author and reviewer are different personas | Block review acceptance; identify the conflict |

## Configuration

- **Default mode:** enforcing (all hooks in this pack are always enforcing; advisory mode is not permitted)
- **Timeout:** 60 seconds per hook
- **Customization:** Projects must specify their control framework in `.foundry/compliance.yml`. The `control-verification` hook reads this file to determine which controls apply. Without a control framework file, the hook passes vacuously with a warning.

## Posture Compatibility

| Posture | Included | Default Mode |
|---------|----------|--------------|
| `baseline` | No | — |
| `hardened` | No | — |
| `regulated` | Yes | enforcing |

This pack is only active at the regulated posture level. It is deliberately excluded from baseline and hardened postures to avoid unnecessary overhead on projects without compliance obligations.

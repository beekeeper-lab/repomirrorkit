# Hook Policy

Policy governing when and how hooks fire during the Foundry team workflow. Hooks are automated checks and actions that run at defined points in the task lifecycle to enforce quality, consistency, and compliance without requiring manual intervention.

## Overview

Hooks exist to catch problems early, enforce standards uniformly, and reduce the burden on reviewers. Rather than relying on personas to remember every check, hooks automate the predictable parts of quality assurance. They act as guardrails: the team moves fast within them, but cannot accidentally skip critical validations.

Hooks are configured per-project through the `hooks` section of the composition spec. The `posture` setting (baseline, hardened, regulated) controls the default set of active hooks. Individual hook packs can be enabled, disabled, or set to advisory mode through the `packs` list.

## Hook Types

| Hook Name | Trigger Event | Purpose | Personas Affected |
|-----------|---------------|---------|-------------------|
| `pre-task-start` | Before a persona begins a task | Validate that all declared inputs are available and dependencies are satisfied | All personas |
| `post-task-complete` | After a persona marks a task done | Validate outputs against acceptance criteria; check that required artifacts exist | All personas |
| `pre-commit` | Before code is committed | Run linting, formatting, and security scans against changed files | Developer, Architect, DevOps |
| `post-integration` | After integration merge completes | Run cross-component tests; verify interface contracts between modules | Integrator, Developer, Tech-QA |
| `pre-release` | Before release packaging | Final compliance verification, changelog validation, license checks | DevOps, Compliance, Security |
| `post-review` | After a code or design review | Verify that all review findings are addressed or explicitly deferred with rationale | Code Quality Reviewer, Tech-QA |
| `pre-seed` | Before task seeding begins | Validate that project objectives are parseable and team composition is complete | Team Lead |

## Hook Execution Rules

### When Hooks Run

- Hooks fire automatically when their trigger event occurs. They cannot be skipped silently -- they either pass, warn, or block.
- Multiple hooks can be bound to the same trigger event. They execute in the order defined by their pack's `order` field, lowest first.
- A hook runs in the context of the triggering persona's current task and has access to the project workspace.

### Execution Order

1. Built-in hooks (from the selected posture) run first.
2. Pack-specific hooks run in pack order.
3. Project-custom hooks run last.

Within the same priority level, hooks execute in alphabetical order by hook name.

### Timeout Policy

- Each hook has a maximum execution time of 60 seconds.
- Hooks that exceed the timeout are treated as failures.
- The timeout can be overridden per-hook in the project's hook configuration, with a hard ceiling of 300 seconds.

## Hook Configuration

### Posture Levels

The `hooks.posture` in the composition spec sets the baseline:

| Posture | Description | Active Hooks |
|---------|-------------|--------------|
| `baseline` | Standard quality checks suitable for most projects | `pre-task-start`, `post-task-complete`, `pre-commit` |
| `hardened` | Stricter checks for production-critical work | All baseline hooks plus `post-integration`, `post-review` |
| `regulated` | Full hook suite for compliance-sensitive projects | All hooks active, all in enforcing mode |

### Enabling and Disabling Hooks

Hooks can be controlled at three levels, with later levels overriding earlier ones:

1. **Posture default** -- The posture sets which hooks are on or off.
2. **Pack override** -- A hook pack in the composition spec can set `enabled: true|false` for specific hooks.
3. **Project override** -- A `.foundry/hooks.yml` file in the project root can override any hook setting for that project only.

### Advisory vs Enforcing Mode

Each hook pack has a `mode` setting:

- **`enforcing`** -- Hook failure blocks the workflow. The triggering action cannot proceed until the hook passes.
- **`advisory`** -- Hook failure produces a warning but does not block. The warning is logged and included in the generation manifest.

## Quality Gates

Some hooks function as quality gates -- hard checkpoints that must pass before the workflow can advance. Quality gate hooks are always in enforcing mode regardless of the pack's mode setting.

| Quality Gate | Trigger | What It Checks |
|--------------|---------|----------------|
| `post-task-complete` | Task marked done | All acceptance criteria checkboxes are checked; required output files exist |
| `pre-commit` | Code commit | No linting errors at error severity; no secrets detected in changed files |
| `post-integration` | Merge complete | All cross-component interface tests pass; no regression in existing tests |
| `pre-release` | Release packaging | Changelog updated; version bumped; compliance checklist complete |

Quality gates cannot be set to advisory mode. If a quality gate fails, the workflow is blocked until the issue is resolved or the gate is explicitly waived by the Team Lead with documented rationale.

## Failure Handling

### Blocking Failures (Enforcing Mode)

When an enforcing hook fails:

1. The triggering action is halted. The task, commit, merge, or release does not proceed.
2. The failure message is displayed to the triggering persona with a clear description of what failed and why.
3. The failure is logged in the generation manifest under `stages.{stage}.warnings`.
4. The persona must fix the issue and re-trigger the action. The hook runs again on retry.

### Non-Blocking Failures (Advisory Mode)

When an advisory hook fails:

1. The triggering action proceeds normally.
2. A warning is displayed to the triggering persona.
3. The warning is logged in the generation manifest.
4. The warning appears in the next `/status-report` output under Risks and Escalations.

### Repeated Failures

If the same hook fails three or more times on the same task, it is flagged as a recurring issue in the status report and an escalation is created for the Team Lead. This prevents silent thrashing where a persona repeatedly retries without addressing the root cause.

## Adding Custom Hooks

Projects can define custom hooks beyond what the library provides. Custom hooks are defined in `.foundry/hooks.yml` in the project root.

### Custom Hook Structure

```yaml
custom_hooks:
  - name: check-api-contracts
    trigger: post-task-complete
    mode: enforcing
    description: Verify that API contract files match the OpenAPI spec
    command: validate-openapi --spec api/openapi.yml --contracts api/contracts/
    timeout: 120
    personas: [developer, architect]

  - name: check-accessibility
    trigger: post-review
    mode: advisory
    description: Run accessibility audit on UI components
    command: a11y-check --components src/components/
    timeout: 90
    personas: [ux-ui-designer, developer]
```

### Custom Hook Rules

- Custom hooks run after all built-in and pack hooks.
- Custom hooks must specify a `trigger`, `mode`, and `description`.
- The `personas` field limits which personas trigger the hook. If omitted, the hook fires for all personas.
- Custom hooks follow the same timeout policy as built-in hooks.
- Custom hooks cannot override or replace built-in quality gates. They can only add additional checks.

## Audit Trail

All hook executions -- pass or fail -- are recorded in the generation manifest. Each entry includes:

- Hook name and trigger event
- Timestamp
- Pass/fail/warn result
- Failure message (if applicable)
- Persona and task context

This audit trail supports retrospectives and compliance reporting. For regulated-posture projects, the audit trail is immutable and must not be edited after generation.

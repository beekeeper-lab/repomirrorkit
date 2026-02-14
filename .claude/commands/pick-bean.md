# /pick-bean Command

Claude Code slash command that lets the Team Lead pick a bean from the backlog for decomposition and execution.

## Purpose

Updates a bean's status from `Approved` to `In Progress` in both the bean's own `bean.md` and the backlog index `_index.md`. This is the Team Lead's formal declaration that a bean has been selected for the current work cycle. Only `Approved` beans can be picked — `Unapproved` beans must be reviewed and approved first.

## Usage

```
/pick-bean <bean-id>
```

- `bean-id` -- The bean ID to pick (e.g., `BEAN-006` or just `6`).

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Bean ID | Positional argument | Yes |

## Process

1. **Resolve bean** -- Parse the bean ID (accept `BEAN-006`, `006`, or `6`). Locate the bean directory in `ai/beans/`.
2. **Validate state** -- Confirm the bean's current status is `Approved` or `Deferred`. Reject if `Unapproved` (not yet reviewed). Warn if already `In Progress`.
3. **Update bean.md** -- Set Status to `In Progress`. Set Owner to `team-lead`. Set `Started` to current timestamp (`YYYY-MM-DD HH:MM`).
4. **Update index** -- Update the matching row in `ai/beans/_index.md` with the new status and owner.
5. **Ensure test branch** -- Check if `test` branch exists locally; create from `main` if missing.
6. **Create feature branch** -- Create and checkout a feature branch: `git checkout -b bean/BEAN-NNN-<slug>`. Branching is mandatory for all beans.
7. **Confirm** -- Display the bean ID, title, new status (`In Progress`), branch name, and a reminder to decompose into tasks.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Updated bean | `ai/beans/BEAN-{NNN}-{slug}/bean.md` | Status, Owner, and Started fields updated |
| Updated index | `ai/beans/_index.md` | Matching row updated |
| Feature branch | `bean/BEAN-NNN-<slug>` | Created and checked out |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `BeanNotFound` | No bean directory matches the given ID | Check `ai/beans/_index.md` for valid IDs |
| `AlreadyActive` | Bean is already `In Progress` by you | No action needed — bean is already active |
| `BeanLocked` | Bean is `In Progress` with a different Owner | Pick a different bean — claimed by another agent |
| `BeanUnapproved` | Bean status is `Unapproved` | Review and approve the bean first |
| `BeanDone` | Bean status is `Done` | Cannot pick a completed bean — create a follow-up bean instead |

## Examples

**Pick an approved bean:**
```
/pick-bean BEAN-006
```
Sets BEAN-006 to `In Progress` status with `team-lead` as owner, creates feature branch `bean/BEAN-006-backlog-refinement`, records `Started` timestamp.

**Pick by short ID:**
```
/pick-bean 3
```
Resolves to BEAN-003, sets status to `In Progress`, creates feature branch.

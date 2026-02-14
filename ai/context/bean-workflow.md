# Bean Workflow

A **Bean** is a unit of work — a feature, enhancement, bug fix, or epic. Beans replace ad-hoc task tracking with a structured, persona-aware workflow.

## Directory Structure

```
ai/beans/
  _index.md                    # Master backlog index
  _bean-template.md            # Template for creating new beans
  _review.md                   # Generated MOC for Obsidian review (auto-generated)
  BEAN-NNN-<slug>/
    bean.md                    # Bean definition (problem, goal, scope, criteria)
    tasks/                     # Task files created during decomposition
      01-<owner>-<slug>.md     # Individual task assigned to a persona
```

## Multi-Agent Environment

Multiple Claude Code agents may be working in this codebase simultaneously. Each agent typically operates in a different functional area (e.g., one on Process beans, another on App beans), but overlap can occur.

**Rules for concurrent work:**
- **Always re-read `_index.md` immediately before creating a new bean** — another agent may have added beans since your last read. Use the highest existing ID + 1.
- **Never pre-assign bean IDs** — during planning, use working titles only. Assign IDs at creation time by reading the current max from `_index.md`.
- **Create beans sequentially, not in parallel** — write each bean's directory + bean.md + index entry before starting the next one. This ensures each bean sees the latest max ID.
- **Always re-read `_index.md` before picking a bean** — another agent may have already picked it.
- **Expect external changes** — files you read earlier may have been modified by another agent. Re-read before editing if significant time has passed.
- **Bean ID collisions** — if you create a bean and find the ID already taken, increment and retry.
- **Don't modify another agent's in-progress bean** — if a bean is `In Progress` with a different owner context, leave it alone.

**Bean locking (claim protocol):**

Beans are locked by their Status + Owner fields in both `_index.md` and `bean.md`. These two fields together act as a lock.

1. **Before picking a bean**, re-read `_index.md`. If the bean's Status is `In Progress` or `Done`, it is locked — skip it. If `Unapproved`, it cannot be picked yet.
2. **To claim a bean**, atomically update both `_index.md` and `bean.md`:
   - Set Status to `In Progress`
   - Set Owner to a unique identifier (e.g., `team-lead`, `agent-2`, or the session context)
3. **A bean is locked when** Status is `In Progress` AND Owner is set. No other agent should pick, modify, or work on a locked bean.
4. **A bean is unlocked when** Status is `Approved` or `Deferred` with no Owner, or Status is `Done`.
5. **If you find a conflict** (you tried to pick a bean but it's already claimed when you go to write), abandon the pick and select a different bean.
6. **Stale locks** — if a bean has been `In Progress` for an unusually long time with no file changes, it may indicate a crashed agent. Do NOT auto-unlock it. Report it to the user and let them decide.

## Bean Lifecycle

```
Unapproved → Approved → In Progress → Done
```

### 1. Creation

Anyone can create a bean:

1. **Re-read `ai/beans/_index.md`** immediately before creation to get the current highest bean ID (another agent may have added beans since your last read)
2. Compute next ID = highest existing + 1
3. Create directory `ai/beans/BEAN-NNN-<slug>/` and copy `_bean-template.md` to `bean.md`
4. Fill in all fields: Problem Statement, Goal, Scope, Acceptance Criteria
5. Set Status to `Unapproved` and assign a Priority
6. Append the bean to `ai/beans/_index.md`

Bean IDs are sequential: BEAN-001, BEAN-002, etc.

**Deferred ID assignment (for batch creation):**

When creating multiple beans at once (e.g., from `/backlog-refinement`), **do not pre-assign IDs during planning**. Use working titles only. Assign IDs one at a time during creation:

1. Plan beans using titles and slugs only (no BEAN-NNN IDs)
2. When ready to create, process beans **sequentially** (not in parallel)
3. For each bean: re-read `_index.md` → assign next ID → write bean.md → append to `_index.md`
4. After all beans are created, update cross-references with the actual IDs

This prevents ID collisions when multiple agents create beans concurrently.

### 2. Approval

Newly created beans have status `Unapproved`. The user must review and approve them before they can be executed. This is the **approval gate** — no work begins without explicit human approval.

**Approval process:**

1. **Review** — Read the bean's Problem Statement, Goal, Scope, and Acceptance Criteria
2. **Evaluate** — Is the scope reasonable? Are criteria testable? Is the priority correct?
3. **Approve** — Change Status from `Unapproved` to `Approved` in both `bean.md` and `_index.md`
4. **Defer** — Optionally change status to `Deferred` for beans that should wait

**What `/long-run` checks:** When the Team Lead enters autonomous mode, it only processes beans with status `Approved`. Beans with status `Unapproved` are skipped entirely. This ensures the user has reviewed and signed off on every unit of work before it begins.

### 3. Picking

The Team Lead reviews the backlog (`ai/beans/_index.md`) and picks beans to work on:

1. **Re-read `_index.md`** — check for beans claimed by other agents since your last read
2. Assess priority and dependencies between beans
3. **Only pick `Approved` beans** — `Unapproved` beans cannot be picked. They must be reviewed and approved first.
4. **Skip locked beans** — any bean with Status `In Progress` and an Owner is claimed by another agent
5. **Claim the bean** — update Status to `In Progress` and set Owner in both `bean.md` and `_index.md`. This is the lock.
6. Update the index table

### 4. Decomposition

The Team Lead breaks each picked bean into tasks:

1. Read the bean's problem statement, goal, and acceptance criteria
2. Create task files in `BEAN-NNN-<slug>/tasks/` with sequential numbering
3. Assign each task an owner (persona) and define dependencies
4. Follow the natural wave: BA → Architect → Developer → Tech-QA
5. Skip personas that aren't needed for a given bean
6. Bean status is already `In Progress` from the picking step

Each task file should include:
- **Owner:** Which persona handles it
- **Depends on:** Which tasks must complete first
- **Goal:** What this task produces
- **Inputs:** What the owner needs to read
- **Definition of Done:** Concrete checklist

### 5. Execution

Each persona claims their task(s) in dependency order:

1. Read the task file and all referenced inputs
2. Produce the required outputs in `ai/outputs/<persona>/`
3. Update the task file with completion status
4. Create a handoff note for downstream tasks if needed

### 6. Verification

The Team Lead reviews completed work:

1. Check each task's Definition of Done
2. Verify outputs match the bean's Acceptance Criteria
3. Run tests and lint
4. Flag any gaps for rework

### 7. Closure

Once all acceptance criteria are met:

1. Update bean status to `Done`
2. Update `ai/beans/_index.md`
3. Note any follow-up beans spawned during execution
4. **Merge feature branch to `test`** using `/merge-bean` (Merge Captain). This step is mandatory — a bean is not fully closed until its branch has been merged to `test` and tests pass on the integrated branch

## Branch Strategy

**Every bean MUST have its own feature branch.** No exceptions. All work happens on the feature branch, never directly on `main`.

### Integration Branch

The standard integration branch is `test`. All completed beans merge into `test` via the Merge Captain. If `test` does not exist, create it from `main`:

```
git checkout -b test main
git push -u origin test
```

Promotion from `test` → `main` happens via the `/deploy` command (a separate, gated process).

### Naming Convention

```
bean/BEAN-NNN-<slug>
```

Examples: `bean/BEAN-006-backlog-refinement`, `bean/BEAN-012-user-auth`

### Lifecycle

1. **Branch creation** — When a bean moves to `In Progress`, create the feature branch immediately:
   ```
   git checkout -b bean/BEAN-NNN-<slug>
   ```
   This is the **first action** after picking a bean. No work happens before the branch exists.
2. **Work on the branch** — All task commits for this bean happen on the feature branch. Never commit to `main`.
3. **Merge to test** — After the bean is verified and closed, the Merge Captain merges the feature branch into `test` using `/merge-bean`.
4. **Cleanup** — After a successful merge, the feature branch is deleted (local + remote).

### Branch Creation Rules

- `/pick-bean` always creates the feature branch (mandatory).
- `/long-run` always creates a feature branch for each bean it processes.
- Manual bean work MUST create the branch when moving to `In Progress`.
- There are no exceptions — even doc-only beans get their own branch.

## Status Values

| Status | Meaning |
|--------|---------|
| `Unapproved` | Created, awaiting human review and approval |
| `Approved` | Reviewed and approved, ready for execution |
| `In Progress` | Tasks have been created and execution is underway |
| `Done` | All acceptance criteria met |
| `Deferred` | Intentionally postponed |

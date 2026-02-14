# Skill: Backlog Consolidation

## Description

Detects and resolves duplicates, scope overlaps, contradictions, missing dependencies, and merge opportunities across recently created beans. Designed for post-refinement cleanup after running multiple `/backlog-refinement` sessions in parallel. The Team Lead analyzes all target beans, presents findings grouped by severity, and iterates with the user to apply agreed changes.

## Trigger

- Invoked by the `/backlog-consolidate` slash command.
- Should only be used by the Team Lead persona.
- Requires `ai/beans/_index.md` and at least 2 beans matching the status filter.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| status | String | No | Which beans to analyze. Default: `Unapproved`. Also accepts `open` (Unapproved + Approved + In Progress), `all`, or any single status value. |
| dry_run | Boolean | No | If true, show findings without applying changes. Defaults to false. |

## Process

### Phase 1: Analysis

1. **Read the backlog** — Parse `ai/beans/_index.md` to get the full bean table. Apply the status filter:
   - `Unapproved` (default): Only beans with Status = Unapproved
   - `open`: Beans with Status = Unapproved, Approved, or In Progress
   - `all`: Every bean regardless of status
   - Any other value: Exact status match

2. **Validate target count** — If zero beans match, report `NoTargetBeans` and stop. If exactly one bean matches, report `SingleBean` and stop. Need at least 2 target beans to compare.

3. **Load all target bean files** — For each target bean, read `ai/beans/BEAN-NNN-<slug>/bean.md` in full. Extract and note:
   - Problem Statement
   - Goal
   - Scope (In Scope and Out of Scope sections)
   - Acceptance Criteria
   - Notes (including any existing dependencies)
   - Priority and Category from the header table

4. **Load Done beans as reference** — Read all beans with Status = Done. These serve as the reference set for detecting duplication of completed work. Only Problem Statement, Goal, and Scope sections are needed from Done beans.

5. **Run the 6 core analysis checks** on every relevant pair:

   **Check 1: Duplicate Detection** (Severity: Critical)
   - Compare the Problem Statement and Goal of every pair of target beans.
   - Flag when two beans describe the same problem in different words.
   - Look for high overlap in key nouns and verbs — e.g., both mention the same module, feature, or user action.
   - Include specific quotes from both beans as evidence.

   **Check 2: Scope Overlap** (Severity: High)
   - Extract file paths, module names, service names, and feature areas from each bean's In Scope section.
   - Flag when two beans reference the same paths or modules.
   - Distinguish between incidental overlap (both touch `_index.md`) and substantive overlap (both modify `generator.py` for the same purpose).
   - Include the specific overlapping items as evidence.

   **Check 3: Contradictions** (Severity: Critical)
   - Look for opposing actions on the same target across any two target beans.
   - Patterns to detect: "add X" vs "remove X", "replace X with Y" vs "enhance X", "consolidate into one" vs "split into many".
   - Check both Acceptance Criteria and Scope sections.
   - Include the specific conflicting statements as evidence.

   **Check 4: Missing Dependencies** (Severity: High)
   - If Bean A's scope creates or modifies something (a file, service, model, or API) that Bean B's scope reads, uses, or depends on, and no dependency is noted in either bean's Notes section, flag it.
   - Check both directions for each pair.
   - Include what is created/modified and what depends on it as evidence.

   **Check 5: Merge Candidates** (Severity: Medium)
   - Identify pairs of beans that share the same Category and similar Priority, where their combined scope would still be a single coherent unit of work.
   - Good merge candidates: two small beans that touch the same area, beans that are sequential steps of the same feature, beans where one is a natural prerequisite contained within the other.
   - Poor merge candidates: beans that would become too large (more than ~8 acceptance criteria combined), beans in different categories, beans with very different priorities.
   - Include the rationale for why merging makes sense as evidence.

   **Check 6: Done Duplication** (Severity: High)
   - Compare each target bean's Problem Statement and Goal against all Done beans.
   - Flag when an Unapproved bean's goal substantially matches work that has already been completed.
   - Include the matching Done bean ID and title, plus the overlapping text as evidence.

6. **Run 2 additional structural checks**:

   **Check 7: Dependency Cycles** (Severity: High)
   - From existing dependency notes across all target beans, build a dependency graph.
   - Detect any cycles (A → B → C → A).
   - Include the full cycle path as evidence.

   **Check 8: Priority Inconsistencies** (Severity: Medium)
   - If a High-priority bean depends on a Low-priority bean that has not been picked yet, flag it — the low bean may need to be promoted.
   - Include the specific beans and their priorities as evidence.

7. **Compile findings** — Group all detected issues by severity: Critical first, then High, then Medium. Number them sequentially.

### Phase 2: Dialogue

8. **Present findings** — Show the user the full list, grouped by severity, with evidence:
   ```
   Found N issues across M beans:

   CRITICAL:
   1. DUPLICATE: BEAN-072 "Add user auth" and BEAN-075 "Authentication system"
      — Both solve the same problem: "The app needs user authentication."
      — Recommend: merge into one bean.

   HIGH:
   2. SCOPE OVERLAP: BEAN-073 and BEAN-076 both modify the project's generator service
      — BEAN-073 In Scope: "Add overlay mode to generator"
      — BEAN-076 In Scope: "Refactor generator pipeline stages"
      — Recommend: add dependency (073 before 076) or merge scope.
   3. DONE DUPLICATION: BEAN-080 "Dark theme support" overlaps Done BEAN-059 "Wire dark theme into app startup"
      — BEAN-080 Goal: "Apply dark theme on app launch"
      — BEAN-059 Goal: "Wire dark theme into app startup sequence"
      — Recommend: delete BEAN-080 or narrow its scope.
   4. MISSING DEPENDENCY: BEAN-074 uses SettingsScreen but BEAN-077 creates it
      — BEAN-074 In Scope: "Add settings persistence via SettingsScreen"
      — BEAN-077 In Scope: "Create SettingsScreen widget"
      — Recommend: add "Depends on BEAN-077" to BEAN-074.

   MEDIUM:
   5. MERGE CANDIDATE: BEAN-078 and BEAN-079 are both small UI tweaks to the wizard
      — Both are App/Low, each has 3 acceptance criteria, both touch wizard pages.
      — Recommend: merge into single bean.
   6. PRIORITY INCONSISTENCY: BEAN-081 (High) depends on BEAN-082 (Low)
      — Recommend: promote BEAN-082 to Medium or High.
   ```

   If no issues are found, report that the backlog looks clean and stop.

9. **For each finding, ask the user what to do** — Present the options relevant to the finding type:

   | Finding Type | Options |
   |-------------|---------|
   | Duplicate | Merge (which title/scope wins?) · Delete one (which?) · Keep both (ignore) |
   | Scope Overlap | Merge · Add dependency (which direction?) · Rewrite scope to remove overlap · Ignore |
   | Contradiction | Rewrite one bean's criteria · Delete one · Rewrite both to be compatible · Ignore |
   | Missing Dependency | Add dependency (which direction?) · Ignore |
   | Merge Candidate | Merge (combined title?) · Keep separate · Add dependency instead |
   | Done Duplication | Delete the New bean · Narrow its scope · Keep it (different enough) |
   | Dependency Cycle | Remove one dependency (which?) · Merge the beans · Restructure scope |
   | Priority Inconsistency | Promote the low bean · Demote the high bean · Ignore |

   Process findings in batches of 2-4 to keep the dialogue manageable. Prioritize Critical findings first.

10. **Iterate** — After the first round of decisions:
    - Re-check for any new issues introduced by the agreed changes (e.g., merging two beans might create a new scope overlap with a third bean, or deleting a bean might break a dependency reference).
    - Present any new findings and repeat the dialogue.
    - Continue until no new issues are detected.

### Phase 3: Execution

11. **Check for dry run** — If `dry_run` is true, skip execution and go to step 16.

12. **Apply agreed changes sequentially** — For each agreed change, in order:

    **Before every write operation:** Re-read `ai/beans/_index.md` to get the latest state. Another agent may have modified it.

    - **Merge two beans:**
      a. Choose the surviving bean (lower ID by default, or as user specified).
      b. Read both bean files.
      c. Combine: use the agreed title, merge both Problem Statements (deduplicate), merge Goals, union of In Scope items, union of Out of Scope items, union of all Acceptance Criteria (deduplicate), combine Notes.
      d. Write the merged content to the surviving bean's `bean.md`.
      e. Remove the deleted bean's directory (`ai/beans/BEAN-NNN-<slug>/`).
      f. Re-read `_index.md`, remove the deleted bean's row, update the surviving bean's title if changed.

    - **Delete a bean:**
      a. Remove the bean's directory (`ai/beans/BEAN-NNN-<slug>/`).
      b. Re-read `_index.md`, remove the bean's row.

    - **Add a dependency:**
      a. Read the target bean's `bean.md`.
      b. Append to the Notes section: `Depends on BEAN-NNN (<title>).`
      c. Write the updated `bean.md`.

    - **Rewrite scope:**
      a. Read the target bean's `bean.md`.
      b. Replace the Scope section with the agreed rewrite.
      c. Write the updated `bean.md`.

    - **Reorder priority:**
      a. Read the target bean's `bean.md`.
      b. Update the Priority field in the header table.
      c. Write the updated `bean.md`.
      d. Re-read `_index.md`, update the Priority column for that bean.

    - **Mark deferred:**
      a. Read the target bean's `bean.md`.
      b. Update the Status field in the header table to `Deferred`.
      c. Write the updated `bean.md`.
      d. Re-read `_index.md`, update the Status column for that bean.

13. **Fix cross-references** — After all changes are applied, scan every remaining target bean's `bean.md` for references to deleted or merged bean IDs. Update them:
    - References to a merged-away bean → point to the surviving bean ID.
    - References to a deleted bean → remove the reference and add a note.

14. **Verify no dependency cycles** — After all changes, rebuild the dependency graph from all modified beans and verify no cycles were introduced.

15. **Verify `_index.md` consistency** — Re-read `_index.md` one final time and confirm:
    - No deleted beans remain in the table.
    - All surviving beans have correct titles, priorities, and statuses.
    - Bean IDs are still unique and sequential.

### Phase 4: Summary

16. **Present a change log** — Show what was done (or would be done, if dry run):
    ```
    Consolidation complete:
    - 2 beans merged (BEAN-072 + BEAN-075 → BEAN-072, BEAN-078 + BEAN-079 → BEAN-078)
    - 1 bean deleted (BEAN-080, duplicate of Done BEAN-059)
    - 3 dependencies added (BEAN-074 depends on BEAN-077, ...)
    - 1 scope rewritten (BEAN-076)
    - 1 priority changed (BEAN-082: Low → Medium)

    Final bean count: 14 (was 17)
    ```

    If dry run, prefix with: `DRY RUN — No changes applied. The following changes would be made:`

17. **Suggest next steps** — Based on findings:
    - If dependencies were added: "Run `/show-backlog` to review the updated dependency graph."
    - If beans were merged: "Review the merged beans to ensure the combined scope is coherent."
    - If many issues were found: "Consider running `/backlog-consolidate` again after making manual adjustments."

## Analysis Heuristics

The agent reads prose and applies judgment. These heuristics guide the analysis:

- **Duplicate detection**: Compare Problem Statements and Goals word by word. If two beans describe the same problem using different words but share the same key nouns (module names, feature names, user actions), flag as duplicate. Examples: "Add user authentication" ≈ "Implement auth system", "Fix generator overlay" ≈ "Repair overlay mode in generator".

- **Scope overlap**: Extract file paths, module names (`generator`, `compiler`), service names (`Scaffold Service`), and feature areas (`wizard pages`, `CLI`) from In Scope sections. If two beans reference the same items, evaluate whether the overlap is incidental (both mention `_index.md` because they add beans) or substantive (both modify the same service logic).

- **Contradictions**: Look for opposing verbs applied to the same target. Key patterns: "add X" vs "remove X", "replace X with Y" vs "enhance X", "consolidate" vs "split", "simplify" vs "extend". Check both Acceptance Criteria and Scope sections.

- **Missing dependencies**: If Bean A's In Scope includes creating or modifying a file/service/model, and Bean B's In Scope includes using or depending on that same artifact, and neither bean's Notes mentions the other, flag the missing dependency.

- **Merge candidates**: Two beans are good merge candidates when they share the same Category and similar Priority, touch the same area of the codebase, and their combined acceptance criteria would total 8 or fewer items. Beans from different categories or with very different priorities are poor candidates.

- **Done duplication**: Compare each target bean's Problem Statement against Done beans' Problem Statements. If the core problem is already solved, flag it. Be precise — a bean that extends Done work ("add feature Y to existing X") is not a duplicate, but a bean that re-solves the same problem is.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| modified_beans | Markdown files | Bean files with updated scope, dependencies, or merged content |
| deleted_beans | Removed directories | Bean directories removed for duplicates |
| updated_index | Markdown file | `_index.md` updated to reflect all changes |
| summary | Console text | Change log with counts of each action taken and final bean count |

## Quality Criteria

- Every finding includes specific evidence (direct quotes from the bean files, not paraphrases).
- No changes are applied without explicit user approval for each finding.
- Merged beans preserve ALL acceptance criteria from both source beans (deduplicating identical items).
- Deleted beans have their references cleaned up in all remaining beans.
- Dependency additions do not create cycles (verified after all changes).
- The `_index.md` is re-read before every write operation (stale-state protection).
- The dialogue phase presents findings in severity order (Critical → High → Medium).
- After applying changes, a re-check confirms no new issues were introduced.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoTargetBeans` | No beans match the status filter | Tell user — nothing to consolidate. Suggest a different `--status` value. |
| `SingleBean` | Only one bean matches — nothing to compare | Tell user — need at least 2 beans to consolidate. |
| `ConcurrentEdit` | Another agent modified a bean or `_index.md` during execution | Abort the current operation, re-read the affected file, report the conflict to the user, and ask how to proceed. |
| `UserAbort` | User decides to cancel mid-consolidation | Stop immediately. No further changes applied. Changes already applied remain (they were individually approved). |

## Dependencies

- Backlog index at `ai/beans/_index.md`
- Bean files at `ai/beans/BEAN-NNN-<slug>/bean.md`
- File system access to delete bean directories (for merge/delete operations)

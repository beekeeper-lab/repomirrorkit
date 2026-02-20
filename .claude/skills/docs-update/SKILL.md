# Skill: Docs Update

## Description

Audits project documentation against the live codebase and fixes stale values. Every fact is gathered by introspection (shell commands, file scans) — nothing is hardcoded. Running twice produces no changes on the second run.

## Trigger

- Invoked by the `/docs-update` slash command.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `--dry-run` | Flag | No | Audit only — print report, do not write changes |

## Protected Paths

**Never modify these directories or their contents:**
- `ai-team-library/` — shared library (read-only)
- `ai/beans/` — bean records (except `_index.md` metadata if needed)
- `ai/outputs/` — persona output archives

If any update would touch a protected path, abort with an error message.

## Process

### Phase 1: Discover

Gather live facts from the codebase. Run these commands and record the results:

#### 1.1 Test Count

```bash
uv run pytest --collect-only -q 2>/dev/null | tail -1
```

Extract the number (e.g., "1811 tests collected"). Record as `$TEST_COUNT`.

#### 1.2 Module/File Lists

```bash
# Service modules
ls foundry_app/services/*.py | grep -v __pycache__ | xargs -I{} basename {} .py | sort

# Core modules
ls foundry_app/core/*.py | grep -v __pycache__ | xargs -I{} basename {} .py | sort

# UI screen files (top-level and nested)
find foundry_app/ui/screens -name "*.py" ! -name "__init__.py" ! -path "*__pycache__*" | sort

# UI widget files
find foundry_app/ui/widgets -name "*.py" ! -name "__init__.py" ! -path "*__pycache__*" | sort

# Top-level app files
ls foundry_app/*.py | grep -v __pycache__ | xargs -I{} basename {} .py | sort
```

Record the complete file lists for the module map.

#### 1.3 Wizard Pages

```bash
ls foundry_app/ui/screens/builder/wizard_pages/*.py | grep -v __init__ | grep -v __pycache__
```

Count the files and extract page names. Record as `$WIZARD_COUNT` and `$WIZARD_NAMES`.

#### 1.4 Bean Counts

```bash
# Total beans and done beans from _index.md
grep -c "^|" ai/beans/_index.md  # approximate total (subtract header rows)
grep -c "Done" ai/beans/_index.md
```

Parse `ai/beans/_index.md` for accurate totals. Record as `$BEAN_TOTAL` and `$BEAN_DONE`.

#### 1.5 Skill and Command Counts

```bash
# User-facing commands
ls .claude/commands/*.md | wc -l

# Skills (directories with SKILL.md)
find .claude/skills -name "SKILL.md" | wc -l
```

Record as `$COMMAND_COUNT` and `$SKILL_COUNT`.

#### 1.6 Git Log for Changelog

```bash
# All beans completed since last tagged release
git log v1.0.0..HEAD --oneline 2>/dev/null || git log --oneline
```

Parse for `BEAN-NNN:` prefixed commit messages. Cross-reference with `ai/beans/_index.md` for bean titles and categories. Group by Keep a Changelog category:
- **Added** — new features, new commands, new services
- **Changed** — enhancements, refactors, workflow changes
- **Fixed** — bug fixes
- **Infrastructure** — process, CI, tooling, documentation

#### 1.7 Directory Tree

Generate a fresh project structure tree by scanning the actual filesystem:

```bash
# Top-level directories
ls -d */

# foundry_app/ tree (2 levels deep, dirs + .py files only)
find foundry_app -maxdepth 3 \( -type d -o -name "*.py" \) ! -path "*__pycache__*" | sort
```

Format the tree to match the README "Project Structure" section style.

### Phase 2: Audit

Compare each discovered fact against the corresponding document location. For each check, output one of:
- `[OK]` — value matches
- `[STALE]` — value exists but is wrong
- `[MISSING]` — expected content not found in the document

#### Audit Checks

| # | Document | Check | How to Compare |
|---|----------|-------|----------------|
| 1 | `CLAUDE.md` | Test count | Look for `pytest test suite (NNN tests)` — compare NNN to `$TEST_COUNT` |
| 2 | `ai/context/project.md` | Test count | Look for `**NNN tests**` or `N tests` — compare to `$TEST_COUNT` |
| 3 | `ai/context/project.md` | Module map | Compare listed files in the module map code block against actual file lists from Phase 1.2 |
| 4 | `ai/context/project.md` | Wizard page count | Look for wizard step count — compare to `$WIZARD_COUNT` |
| 5 | `README.md` | Project structure tree | Compare the code block under "## Project Structure" against actual tree from Phase 1.7 |
| 6 | `README.md` | Wizard page count | Look for wizard step count references — compare to `$WIZARD_COUNT` |
| 7 | `README.md` | Phantom files | Check that every file listed in the tree actually exists |
| 8 | `CHANGELOG.md` | Unreleased section | Check if an `[Unreleased]` section exists with beans completed since last release |
| 9 | `MEMORY.md` | Test count | Look for test count in "Current Status" — compare to `$TEST_COUNT` |
| 10 | `MEMORY.md` | Module count | Look for module count in "Current Status" — compare to actual count |

#### Audit Output Format

```
=== Documentation Audit ===

CLAUDE.md
  [STALE] Test count: says 248, actual 1811

ai/context/project.md
  [STALE] Test count: says 248, actual 1811
  [STALE] Module map: 3 missing files, 2 phantom files
  [STALE] Wizard pages: says 4, actual 6

README.md
  [STALE] Project structure: 2 phantom files, 1 missing dir
  [STALE] Wizard pages: says 4, actual 6
  [OK]    Command tables

CHANGELOG.md
  [MISSING] No [Unreleased] section

MEMORY.md
  [STALE] Test count: says 1235, actual 1811

Summary: 7 stale, 1 missing, 1 ok — 8 fixes needed
```

**If `--dry-run`**: Print the audit report and stop. Do not proceed to Phase 3.

### Phase 3: Update

Fix each `[STALE]` or `[MISSING]` finding. For each document:

#### 3.1 CLAUDE.md

Find the line containing `pytest test suite (NNN tests)` and replace NNN with `$TEST_COUNT`.

#### 3.2 ai/context/project.md

- **Test count**: Find and replace the test count value with `$TEST_COUNT`.
- **Module map**: Regenerate the entire module map code block from scratch using the file lists from Phase 1.2. Do not patch — replace the whole block. Follow the existing format (indented tree with `# comment` annotations).
- **Wizard page count**: Update wizard step references to `$WIZARD_COUNT` and list actual page names.

#### 3.3 README.md

- **Project structure tree**: Regenerate the entire tree under "## Project Structure" from the actual filesystem scan in Phase 1.7. Follow the existing format with `# comment` annotations. Remove phantom files, add missing entries.
- **Wizard page count**: Find wizard step count references (e.g., "4-step wizard" or "4-step guided flow") and update to `$WIZARD_COUNT`.
- **Command tables**: If the Quick Reference table under "Skills & Commands Summary" is missing any commands from `.claude/commands/`, add them. Remove any that no longer exist.

#### 3.4 CHANGELOG.md

If no `[Unreleased]` section exists, add one immediately after the header and before the `[1.0.0]` section. Group beans by Keep a Changelog category:

```markdown
## [Unreleased]

### Added
- BEAN-NNN: Short description of new feature

### Changed
- BEAN-NNN: Short description of enhancement

### Fixed
- BEAN-NNN: Short description of bug fix

### Infrastructure
- BEAN-NNN: Short description of process/tooling change
```

Use the bean title from `_index.md` as the description. One bullet per bean. Sort by bean number within each category.

If an `[Unreleased]` section already exists, merge any new beans into it (do not duplicate).

#### 3.5 MEMORY.md

Update the "Current Status" section:
- Test count: replace with `$TEST_COUNT`
- Module count: replace with the actual count from Phase 1.2

### Phase 4: Verify

Re-run all audit checks from Phase 2 on the updated files. Every check must return `[OK]`.

If any check still returns `[STALE]` or `[MISSING]`:
1. Print the failing checks with details
2. Do NOT proceed to Phase 5
3. Report which updates failed and why

Also verify:
- No files in protected paths were modified (check git diff for `ai-team-library/`, `ai/beans/` content files, `ai/outputs/`)
- All modified files are valid markdown (no broken syntax from the edits)

### Phase 5: Commit

Create a single atomic commit with all documentation changes:

```bash
git add CLAUDE.md README.md ai/context/project.md CHANGELOG.md
# Only add MEMORY.md if it was changed
git add -N ~/.claude/projects/*/memory/MEMORY.md 2>/dev/null
```

Commit message format:
```
Update project documentation to match codebase

- Test count: NNN (was XXX in CLAUDE.md, YYY in project.md)
- Module map regenerated in project.md
- Project structure tree regenerated in README.md
- [Unreleased] changelog section added with N beans
- MEMORY.md current status updated
```

## Key Design Properties

- **Introspection-driven**: All facts come from shell commands and file scans, never hardcoded values
- **Idempotent**: Running twice produces no changes on the second run (all checks return `[OK]`)
- **Non-destructive**: Protected paths are never modified; module maps and trees are regenerated (not patched)
- **Auditable**: The audit report shows exactly what will change before any writes happen

## Error Conditions

| Error | Resolution |
|-------|------------|
| `pytest --collect-only` fails | Report error, use "unknown" for test count, skip test-count checks |
| Protected path in write set | Abort immediately with error message |
| Verify phase failures | Report failing checks, do not commit |
| No stale findings | Report "All documentation is up to date" and exit |
| Git commit fails | Report error, leave files modified but uncommitted |

## Quality Criteria

- All audit checks pass after update (`[OK]` across the board)
- No protected paths modified
- Commit contains only documentation files
- Running `/docs-update --dry-run` immediately after shows all `[OK]`

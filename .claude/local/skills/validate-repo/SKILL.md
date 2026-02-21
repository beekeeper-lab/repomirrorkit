# Skill: Validate Repo

## Description

Runs a comprehensive health check against a generated project or any repo that
follows the Foundry structure. Verifies folder expectations, required files,
template completeness, broken internal links, and stack-specific tooling
(lint, test, build commands). Produces a pass/fail checklist with actionable
remediation for every finding. This skill works on any project regardless of
stack because it adapts its checks based on the composition spec.

## Trigger

- Invoked by the `/validate-repo` slash command.
- Can be run at any point during a project's lifecycle as a health check.
- Useful as a pre-export gate before sharing a generated project.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| project_dir | Directory path | Yes | Root of the project to validate |
| composition_spec | YAML file path | No | Composition spec; defaults to `ai/team/composition.yml` in the project |
| check_level | Enum: `structure`, `content`, `full` | No | Depth of validation; defaults to `full` |

## Process

1. **Locate composition spec** -- Find and parse `ai/team/composition.yml` from the project directory. If missing, run structural checks only.
2. **Validate folder structure** -- Confirm all expected directories exist: `.claude/agents/`, `ai/context/`, `ai/generated/members/`, `ai/team/`, `ai/tasks/`, `ai/outputs/`.
3. **Check required files** -- Verify `CLAUDE.md`, `README.md`, `ai/team/composition.yml` exist and are non-empty.
4. **Validate agent completeness** -- For each persona in the composition, confirm `.claude/agents/{id}.md` and `ai/generated/members/{id}.md` exist.
5. **Check output directories** -- Verify `ai/outputs/{id}/` exists for each persona.
6. **Scan for broken internal links** -- Parse all markdown files for relative links and verify targets exist on disk.
7. **Run stack-specific checks** -- Based on the stacks in the composition:
   - `python`: Check for `pyproject.toml` or `setup.py`; verify `pytest` or test command is runnable.
   - `node`/`react`/`typescript`: Check for `package.json`; verify `npm test` or equivalent exists.
   - `java`: Check for `pom.xml` or `build.gradle`.
   - `dotnet`: Check for `*.csproj` or `*.sln`.
   - Other stacks: Check for common entry points.
8. **Check for secrets exposure** -- Scan for `.env` files, hardcoded API keys, or credentials patterns in tracked files.
9. **Verify manifest consistency** -- If `ai/generated/manifest.json` exists, confirm the files it lists still exist on disk.
10. **Produce validation report** -- Generate a checklist with pass/fail/warn per check and remediation guidance for failures.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| validation_report | Markdown file | Structured checklist with status per check and remediation steps |
| exit_code | Integer | 0 if all checks pass, 1 if any errors, 2 if warnings only |

## Quality Criteria

- Every check produces a clear pass, fail, or warn verdict with no ambiguous states.
- Failed checks include specific remediation: what file to create, what command to run, what to fix.
- Stack-specific checks only run for stacks listed in the composition; missing stacks do not produce false failures.
- The report is sorted by severity: errors first, then warnings, then passes.
- Running validation on a freshly-generated project produces zero errors and zero warnings.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `ProjectDirNotFound` | The specified directory does not exist | Check the path |
| `NotAFoundryProject` | No `CLAUDE.md` or `ai/` directory found | Verify this is a Foundry-generated project |
| `CompositionParseError` | The composition spec is malformed | Fix the YAML in `ai/team/composition.yml` |
| `StackCheckUnavailable` | A stack-specific tool is not installed | Install the required tool or skip stack checks with `--check-level structure` |

## Dependencies

- `foundry_app/services/validator.py` -- existing validation logic for composition and library checks
- `foundry_app/services/export.py` -- `validate_generated_project()` for structural checks
- Access to the project directory's filesystem
- Stack-specific tooling (pytest, npm, etc.) for full validation

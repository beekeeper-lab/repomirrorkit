# /validate-repo Command

Claude Code slash command that runs a comprehensive health check on a Foundry project.

## Purpose

Verify that a project's structure, files, internal links, and stack-specific tooling are all in good shape. Catches missing files, broken references, secrets exposure, and configuration drift before they cause problems during development or export.

## Usage

```
/validate-repo [project-dir] [--check-level <structure|content|full>]
```

- `project-dir` -- Path to the project root. Defaults to the current working directory.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Project directory | Positional argument or cwd | Yes |
| Composition spec | `ai/team/composition.yml` in the project | No (degrades to structural checks) |

## Process

1. **Locate project and composition** -- Find the project root and parse its composition spec.
2. **Run structural checks** -- Verify all expected directories and required files exist.
3. **Run Claude-Kit integration check** -- Execute `scripts/claude-kit-check.sh` to verify submodule presence, symlink wiring, layout correctness, and absence of legacy artifacts. If `--fix` is set, pass `--fix` to the script. This check runs at all check levels (structure, content, full).
4. **Run content checks** -- Validate agent completeness, output directories, internal links, manifest consistency.
5. **Run stack checks** -- Execute stack-specific validations based on the composition's stack selections.
6. **Produce report** -- Output a pass/fail/warn checklist with remediation guidance.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Validation report | stdout (or `--output` path) | Structured checklist with verdicts and remediation |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--check-level <level>` | `full` | `structure`: folders and files only. `content`: adds link and completeness checks. `full`: adds stack-specific and secrets checks |
| `--output <path>` | stdout | Write the report to a file instead of stdout |
| `--strict` | `false` | Treat warnings as errors |
| `--fix` | `false` | Attempt to auto-fix simple issues (create missing directories, add missing READMEs, repair Claude-Kit symlinks) |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `ProjectDirNotFound` | Directory does not exist | Check the path |
| `NotAFoundryProject` | No CLAUDE.md or ai/ directory | Verify this is a Foundry-generated project |
| `StackToolMissing` | Stack-specific tool not installed | Install the tool or use `--check-level content` to skip stack checks |

## Examples

**Validate the current project:**
```
/validate-repo
```
Runs a full health check on the current working directory.

**Structural check only:**
```
/validate-repo ./generated-projects/my-app --check-level structure
```
Checks only that the expected directories and files exist, skipping content and stack checks.

**Strict mode for CI:**
```
/validate-repo --strict
```
Treats all warnings as errors; useful in CI pipelines where any issue should fail the build.

**Auto-fix simple issues:**
```
/validate-repo --fix
```
Creates missing directories and stub files where possible, then re-validates.

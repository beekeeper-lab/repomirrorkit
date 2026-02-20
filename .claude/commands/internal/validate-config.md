# /validate-config Command

Claude Code slash command that checks configuration hygiene and detects exposed secrets.

## Purpose

Catch hardcoded secrets, missing config variables, untracked .env files, and cross-environment inconsistencies before they cause outages or security incidents. This is the config equivalent of running a linter -- it catches the common mistakes that break deployments and leak credentials.

## Usage

```
/validate-config [project-dir] [--schema <path>] [--environments <list>]
```

- `project-dir` -- Project root. Defaults to current working directory.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Project directory | Positional argument or cwd | Yes |
| Config schema | `--schema` flag | No |
| Secret patterns | `--patterns` flag | No (uses built-in patterns) |
| Environments | `--environments` flag | No |

## Process

1. **Discover config files** -- Find .env, config, settings, and similar files.
2. **Scan for secrets** -- Check all files for hardcoded credentials and keys.
3. **Validate .env hygiene** -- Confirm .gitignore, .env.example, no committed secrets.
4. **Check schema** -- Validate config variables against schema if provided.
5. **Cross-env check** -- Verify consistency across environments.
6. **Report** -- Produce findings with severity and remediation.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Config report | stdout (or `--output` path) | Findings with severity, location, and remediation |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--schema <path>` | None | Config schema file for validation |
| `--patterns <path>` | Built-in | Custom secret detection patterns |
| `--environments <list>` | None | Comma-separated environments to validate (e.g., `dev,staging,prod`) |
| `--output <path>` | stdout | Write the report to a file |
| `--severity <level>` | `all` | Minimum severity to report: `critical`, `error`, `warning`, `info`, `all` |
| `--fix-gitignore` | `false` | Auto-add .env to .gitignore if missing |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `ProjectDirNotFound` | Directory does not exist | Check the path |
| `SchemaParseError` | Config schema is malformed | Fix the schema file |

## Examples

**Check the current project:**
```
/validate-config
```
Scans for hardcoded secrets, checks .env hygiene, and reports findings.

**Validate against a schema:**
```
/validate-config --schema config/schema.json --environments dev,staging,prod
```
Validates all config files against the schema and checks consistency across environments.

**Critical issues only:**
```
/validate-config --severity critical
```
Only reports exposed secrets and other critical findings.

**Auto-fix .gitignore:**
```
/validate-config --fix-gitignore
```
Adds `.env` to `.gitignore` if it's missing. Other fixes are reported but not auto-applied.

**CI mode:**
```
/validate-config --severity error
```
Returns exit code 1 if any error or critical findings exist; suitable for CI pipeline gates.

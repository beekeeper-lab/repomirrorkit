# Skill: Validate Config

## Description

Checks configuration and secrets hygiene across the project. Detects hardcoded
secrets, validates environment variable usage, verifies config schemas, ensures
secrets come from expected sources (env vars, secret managers, encrypted files),
and flags configuration that would break across environments. This skill catches
the class of bugs where code works on one machine but fails in staging or
production because of config assumptions.

## Trigger

- Invoked by the `/validate-config` slash command.
- Called by the Security Engineer or DevOps persona during pre-release checks.
- Useful as a pre-commit hook for catching secrets before they enter version control.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| project_dir | Directory path | Yes | Root of the project to scan |
| config_schema | File path | No | Schema file defining expected config variables and types |
| secret_patterns | File path | No | Custom patterns for secret detection; defaults to built-in patterns |
| environment_list | List of strings | No | Environments to validate against (e.g., "dev", "staging", "prod") |

## Process

1. **Discover config files** -- Find all configuration files: `.env`, `.env.*`, `config.*`, `settings.*`, `application.*`, `docker-compose.*`, `*.toml`, `*.ini`, `*.cfg`. Build an inventory.
2. **Scan for hardcoded secrets** -- Check all project files (not just config) for patterns matching:
   - API keys (long alphanumeric strings assigned to key-like variable names)
   - Passwords (variables named password, secret, token, etc. with literal values)
   - Connection strings with embedded credentials
   - Private keys (PEM headers, SSH key patterns)
   - Cloud provider credentials (AWS access keys, GCP service account keys)
3. **Validate .env usage** -- If `.env` files exist:
   - Confirm `.env` is in `.gitignore`
   - Check that a `.env.example` or `.env.template` exists documenting required variables
   - Verify `.env` values are not committed to version control
4. **Check config schema** -- If a config schema is provided, validate that all required config variables are defined and have valid types/formats. Flag missing required variables and type mismatches.
5. **Validate cross-environment consistency** -- For each environment in the list, check that environment-specific config files exist and define all required variables. Flag variables present in dev but missing in prod.
6. **Check secret sourcing** -- Verify that secrets reference environment variables or secret managers rather than file literals. Flag any config that reads secrets from committed files.
7. **Produce validation report** -- Generate a report with findings categorized as: critical (exposed secrets), error (missing required config), warning (missing .env.example, inconsistent envs), info (recommendations).

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| config_report | Markdown file | Validation findings with severity, location, and remediation |
| secrets_findings | Section in report | List of potential secret exposures with file:line references |
| config_completeness | Section in report | Missing or misconfigured variables per environment |

## Quality Criteria

- Secret detection has low false-positive rate: variable names and context are used, not just pattern matching on random strings.
- Every finding includes the file path and line number where the issue was found.
- Critical findings (exposed secrets) are clearly distinguished from warnings (missing .env.example).
- The report includes remediation steps: how to move a hardcoded secret to an env var, how to create a .env.example, etc.
- Running this skill on a freshly-generated Foundry project produces zero critical or error findings.
- The skill does not flag secrets in test fixtures or documentation examples as critical (uses context to distinguish).

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `ProjectDirNotFound` | Directory does not exist | Check the path |
| `SchemaParseError` | Config schema file is malformed | Fix the schema file format |
| `NoConfigFound` | No configuration files found in the project | May be intentional for simple projects; the skill reports this as info |

## Dependencies

- No external tooling required; the skill operates on file content analysis
- `.gitignore` file for checking whether sensitive files are tracked
- Git status (optional) to verify whether .env files are committed

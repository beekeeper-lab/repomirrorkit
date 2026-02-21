# /threat-model Command

Claude Code slash command that performs a STRIDE threat analysis on a system architecture.

## Purpose

Systematically identify security threats by analyzing trust boundaries, data flows, and entry points against the six STRIDE categories. Produces a threat model with risk ratings, mitigations, and a testable security checklist. Essential for hardened and regulated posture projects; valuable for any project handling user data.

## Usage

```
/threat-model <architecture-doc> [--scope <component>] [--update <existing-model>]
```

- `architecture-doc` -- Path to the architecture spec or design document to analyze.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Architecture doc | Positional argument | Yes |
| Project context | `ai/context/project.md` (auto-detected) | No |
| Scope | `--scope` flag | No |
| Existing model | `--update` flag | No |

## Process

1. **Parse architecture** -- Extract components, data stores, external services, and user types.
2. **Identify trust boundaries and data flows** -- Map where trust levels change.
3. **Apply STRIDE** -- Evaluate each boundary for all six threat categories.
4. **Rate and mitigate** -- Assign risk levels and propose specific mitigations.
5. **Generate checklist** -- Produce testable items for each mitigation.
6. **Write output** -- Save the threat model and security checklist.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Threat model | `ai/outputs/security-engineer/threat-model.md` | Complete STRIDE analysis |
| Security checklist | `ai/outputs/security-engineer/security-checklist.md` | Testable verification items |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--scope <component>` | Entire system | Limit analysis to a specific component or subsystem |
| `--update <path>` | None | Update an existing threat model incrementally |
| `--output <dir>` | `ai/outputs/security-engineer/` | Override the output directory |
| `--risk-threshold <level>` | `medium` | Only include threats at or above this risk level in the checklist |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoArchitectureDoc` | File not found | Provide a valid path to an architecture document |
| `EmptyArchitecture` | Document has no substantive content | Flesh out the architecture doc with components and data flows |
| `ScopeNotFound` | Scope does not match any component | Check component names in the architecture doc |

## Examples

**Full system analysis:**
```
/threat-model ai/outputs/architect/design-spec.md
```
Analyzes the entire system architecture and produces a threat model.

**Scoped analysis:**
```
/threat-model ai/outputs/architect/design-spec.md --scope "authentication subsystem"
```
Focuses the STRIDE analysis on the authentication subsystem only.

**Update existing model:**
```
/threat-model ai/outputs/architect/design-spec-v2.md --update ai/outputs/security-engineer/threat-model.md
```
Incrementally updates the threat model based on architecture changes.

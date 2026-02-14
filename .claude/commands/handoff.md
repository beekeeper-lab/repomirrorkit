# /handoff Command

Claude Code slash command that creates a structured handoff packet between personas.

## Purpose

Package everything the next persona needs to pick up where the previous one left off. When the Architect finishes the design and the Developer needs to start implementing, or when the Developer finishes and Tech-QA needs to verify, the handoff packet bundles the artifacts, decisions, assumptions, next steps, and risks into one document. No context lost between the baton pass.

## Usage

```
/handoff <from-persona> <to-persona> [--work <id>] [--notes <text>]
```

- `from-persona` -- The persona completing their phase.
- `to-persona` -- The persona picking up next.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| From persona | Positional argument | Yes |
| To persona | Positional argument | Yes |
| Work ID | `--work` flag | No |
| Artifacts | `--artifacts` flag or auto-detected | No |
| Notes | `--notes` flag | No |

## Process

1. **Gather artifacts** -- Collect the sender's outputs from `ai/outputs/{from}/`.
2. **Summarize deliverables** -- One-line summary per artifact with path and status.
3. **Capture decisions and assumptions** -- Extract from artifacts and ADRs.
4. **Define next steps** -- What the receiver should do, referencing task specs.
5. **Flag risks** -- Open questions and unresolved items.
6. **Write packet** -- Save to `ai/handoffs/`.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Handoff packet | `ai/handoffs/{from}-to-{to}-{work-id}.md` | Structured handoff document |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--work <id>` | None | Work item ID to scope the handoff (e.g., `WRK-003`) |
| `--artifacts <paths>` | Auto-detected | Comma-separated artifact paths to include |
| `--notes <text>` | None | Free-form context to include in the handoff |
| `--output <path>` | `ai/handoffs/` | Override the output directory |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `FromPersonaNotFound` | Persona not in the team composition | Check persona ID |
| `ToPersonaNotFound` | Persona not in the team composition | Check persona ID |
| `NoArtifactsFound` | No outputs from the sender | Verify work is complete or list artifacts explicitly |
| `SamePersona` | From and to are the same | Handoff requires two different personas |

## Examples

**Architect to Developer:**
```
/handoff architect developer --work WRK-003
```
Packages the Architect's design spec, ADRs, and review checklist into a handoff for the Developer. Lists what to implement, key design decisions, and assumptions about the tech stack.

**Developer to Tech-QA:**
```
/handoff developer tech-qa --work WRK-003 --notes "Edge case around null emails is handled in middleware, not in the controller. See auth-middleware.ts:45."
```
Packages the Developer's implementation with a specific note about where to focus testing.

**BA to Architect:**
```
/handoff ba architect
```
Packages all BA stories and the epic brief for the Architect to begin design. No work ID needed if there's only one active work stream.

**With explicit artifacts:**
```
/handoff security-engineer developer --artifacts ai/outputs/security-engineer/threat-model.md,ai/outputs/security-engineer/security-checklist.md
```
Creates a handoff with only the specified files rather than the full output directory.

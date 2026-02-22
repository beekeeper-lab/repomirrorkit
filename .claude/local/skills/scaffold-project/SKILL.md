# Skill: Scaffold Project

## Description

Creates the standard project folder structure from a composition spec. Produces
the repo skeleton that all other skills and personas operate within: CLAUDE.md,
`.claude/` agent/skill/hook directories, `ai/` context and output directories,
README, and per-persona output folders. This is the structural foundation step
in the Foundry pipeline (Select --> Compose --> Compile --> **Scaffold** --> Seed --> Export).

## Trigger

- Invoked by the `/scaffold-project` slash command.
- Called programmatically by `foundry_app/services/scaffold.py` during pipeline execution.
- Runs automatically as part of `foundry-cli generate`.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| composition_spec | YAML file path | Yes | The composition defining project identity, personas, stacks, and hooks |
| output_dir | Directory path | No | Where to create the project; defaults to `{output_root}/{slug}` from the spec |

## Process

1. **Parse the composition spec** -- Load and validate the YAML against the CompositionSpec model.
2. **Create root directory** -- Create `{output_dir}/` if it does not exist.
3. **Generate CLAUDE.md** -- Produce the project's top-level Claude Code constitution listing team members, stacks, hooks posture, and project structure.
4. **Generate README.md** -- Create a minimal README linking to CLAUDE.md.
5. **Create .claude/ directories** -- Create `agents/`, `skills/`, `commands/`, and `hooks/` under `.claude/`.
6. **Generate agent wrappers** -- For each persona with `include_agent: true`, write a thin `.claude/agents/{persona}.md` that references the compiled member prompt path and output directory.
7. **Create ai/ directories** -- Create `context/`, `generated/members/`, `team/`, `tasks/`, and `outputs/` under `ai/`.
8. **Generate project context docs** -- Write `ai/context/project.md` (project overview with stacks, personas, hooks detail, team responsibilities, conventions), `ai/context/stack.md`, and `ai/context/decisions.md`.
9. **Write composition snapshot** -- Serialize the composition spec to `ai/team/composition.yml` for reproducibility.
10. **Create per-persona output directories** -- For each persona, create `ai/outputs/{persona}/` with a README explaining the directory's purpose.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| CLAUDE.md | File | Top-level project constitution for Claude Code |
| README.md | File | Project README with pointer to CLAUDE.md |
| .claude/agents/*.md | Files | Thin agent wrappers for each active persona |
| ai/context/*.md | Files | Project context, stack context, and decisions documents |
| ai/team/composition.yml | File | Serialized composition spec snapshot |
| ai/outputs/*/README.md | Files | Per-persona output directory with README |

## Quality Criteria

- Every persona with `include_agent: true` has a corresponding `.claude/agents/{id}.md` file.
- Every persona has an `ai/outputs/{id}/` directory with a README.
- CLAUDE.md lists all personas, stacks, and the hooks posture.
- `ai/context/project.md` contains team responsibilities and stack conventions.
- `ai/team/composition.yml` round-trips through the CompositionSpec model without data loss.
- All directory structures are created regardless of whether subsequent pipeline stages run.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `InvalidCompositionSpec` | YAML fails schema validation | Fix the composition YAML to match the CompositionSpec model |
| `OutputDirNotWritable` | Cannot create the output directory | Check filesystem permissions or choose a different path |
| `OutputDirExists` | Output directory already contains files | Use `--force` to overwrite or choose a clean directory |

## Dependencies

- `foundry_app/core/models.py` -- CompositionSpec data contract
- `foundry_app/services/scaffold.py` -- reference implementation
- No other skills are required before scaffolding; this is the first structural step

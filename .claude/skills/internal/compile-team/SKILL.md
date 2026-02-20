# Skill: Compile Team

## Description

Assembles a complete team configuration from AI Team Library components. Resolves
persona, stack, and workflow references from a composition spec, checks for
dependency conflicts, merges all resolved content into a unified CLAUDE.md
constitution, and produces a generation manifest recording exactly what was
compiled and from where. This is the core build step in the Foundry pipeline
(Select --> Compose --> **Compile** --> Scaffold --> Seed --> Export).

## Trigger

- Invoked by the `/compile-team` slash command.
- Called programmatically by `foundry_app/services/compiler.py` during pipeline execution.
- Can be run standalone for dry-run validation without writing output files.

## Inputs

| Input                  | Type                              | Required | Description                                                        |
|------------------------|-----------------------------------|----------|--------------------------------------------------------------------|
| composition_spec       | YAML file path                    | Yes      | The composition defining personas, stacks, and workflows to include |
| library_path           | Directory path                    | Yes      | Root of the ai-team-library (contains personas/, stacks/, workflows/) |
| output_dir             | Directory path                    | No       | Where to write compiled output; defaults to `./build/`             |
| validation_strictness  | Enum: `light`, `standard`, `strict` | No    | Validation level; defaults to `standard`                           |

## Process

1. **Parse and validate the composition spec** -- Load the YAML, validate against the CompositionSpec Pydantic model, and reject malformed input early.
2. **Resolve persona references** -- For each persona listed in the spec, load `persona.md`, `outputs.md`, `prompts.md`, and any files under `templates/` from the library.
3. **Resolve stack references** -- For each stack listed, load `conventions.md` and associated skill files from `stacks/{stack}/`.
4. **Resolve workflow references** -- Load any workflow definitions referenced in the spec from `workflows/`.
5. **Check for dependency conflicts** -- Detect missing references, circular dependencies, duplicate persona slots, or incompatible stack combinations.
6. **Merge all resolved content into a unified CLAUDE.md** -- Concatenate sections in deterministic order: project header, persona definitions, stack conventions, workflow rules, and shared instructions.
7. **Generate a generation manifest** -- Record every source file consumed, its content hash, the timestamp, and the library version, producing a `generation-manifest.json`.

## Outputs

| Output               | Type       | Description                                                        |
|----------------------|------------|--------------------------------------------------------------------|
| compiled_claude_md   | File       | Unified CLAUDE.md team constitution ready for deployment           |
| generation_manifest  | JSON file  | Record of every source file, content hash, and compile metadata    |
| validation_report    | Text       | Warnings, info messages, or errors encountered during compilation  |

## Quality Criteria

- Every persona referenced in the composition spec is fully resolved (persona.md, outputs.md, prompts.md all present).
- Every stack referenced has a conventions.md loaded.
- The compiled CLAUDE.md contains no unresolved placeholders or template variables.
- The generation manifest lists every source file with a valid content hash.
- Compilation is deterministic: the same inputs always produce byte-identical outputs.
- Validation report surfaces all warnings even when compilation succeeds.

## Error Conditions

| Error                        | Cause                                              | Resolution                                              |
|------------------------------|----------------------------------------------------|---------------------------------------------------------|
| `InvalidCompositionSpec`     | YAML fails schema validation                       | Fix the composition YAML to match the CompositionSpec model |
| `PersonaNotFound`            | Persona name in spec has no matching library folder | Check spelling; ensure the persona exists under `personas/` |
| `StackNotFound`              | Stack name in spec has no matching library folder   | Check spelling; ensure the stack exists under `stacks/`    |
| `MissingRequiredFile`        | A persona directory lacks persona.md or outputs.md  | Add the missing file to the persona's library directory    |
| `DependencyConflict`         | Two stacks or personas declare incompatible rules   | Remove one conflicting entry or resolve the conflict manually |
| `OutputDirectoryNotWritable` | The output_dir path is not writable                 | Check filesystem permissions or choose a different path    |

## Dependencies

- **Validate Composition** skill (or inline validation via Pydantic models)
- Access to the ai-team-library file tree (personas/, stacks/, workflows/)
- `foundry_app/core/models.py` -- CompositionSpec and GenerationManifest data contracts
- `foundry_app/services/compiler.py` -- reference implementation of the compile logic

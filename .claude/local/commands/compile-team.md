# /compile-team Command

Claude Code slash command that compiles selected personas, stacks, and workflows into a complete team configuration ready for use in a project workspace.

## Purpose

Assemble a unified `CLAUDE.md` file and supporting artifacts from the AI Team Library. The command reads a composition spec (which personas, stacks, and hooks were selected), resolves all references against the library, and produces a single compiled output that Claude Code can consume as its operating instructions for the project.

## Usage

```
/compile-team [composition-file]
```

- `composition-file` -- Path to a `composition.yml` file. Defaults to `./ai/team/composition.yml` if omitted.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Composition spec | `composition.yml` (YAML) | Yes |
| Library root | `ai-team-library/` directory | Yes |
| Stack overrides | `stack_overrides.notes_md` in composition spec | No |
| Generation options | `generation` block in composition spec | No |

The composition spec must conform to the `CompositionSpec` data contract, including `project`, `stacks`, `team.personas`, `hooks`, and `generation` sections.

## Process

1. **Load composition spec** -- Parse the YAML file and validate it against the `CompositionSpec` schema. Reject malformed or missing fields early.
2. **Build library index** -- Scan the library root to discover available personas, stacks, and hooks. Produce a `LibraryIndex` for resolution.
3. **Validate references** -- Confirm every persona ID in `team.personas` and every stack ID in `stacks` exists in the library index. Collect all missing references as errors.
4. **Compile persona blocks** -- For each selected persona, merge `persona.md`, `outputs.md`, and `prompts.md` into a single persona section. Respect the `strictness` setting (light, standard, strict) to control how much of each file is included.
5. **Merge stack conventions** -- Concatenate the conventions from each selected stack in the order specified by `stack.order`. Apply any `stack_overrides.notes_md` content as an addendum.
6. **Resolve hook configuration** -- Include hook definitions based on the `hooks.posture` (baseline, hardened, regulated) and any per-pack overrides.
7. **Produce unified CLAUDE.md** -- Assemble all compiled sections into a single markdown file with a standard structure: project identity, stack conventions, persona instructions, hook policies, and generation metadata.
8. **Write manifest** -- If `generation.write_manifest` is true, produce a `manifest.json` recording every file written, warnings encountered, and the composition snapshot.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| `CLAUDE.md` | `{output_root}/{output_folder}/CLAUDE.md` | Unified team instructions for Claude Code |
| `manifest.json` | `{output_root}/{output_folder}/ai/generated/manifest.json` | Generation manifest with file list and metadata |
| Persona templates | `{output_root}/{output_folder}/ai/templates/{persona}/` | Copied template files for each persona with `include_templates: true` |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--output-dir <path>` | From composition spec | Override the output directory |
| `--strict` | `false` | Treat all warnings as errors; abort on any validation issue |
| `--dry-run` | `false` | Validate and report what would be generated without writing files |
| `--no-manifest` | `false` | Skip writing the generation manifest |
| `--verbose` | `false` | Print detailed progress for each compilation stage |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `CompositionFileNotFound` | The specified composition file does not exist | Check the path; default is `./ai/team/composition.yml` |
| `InvalidCompositionSpec` | YAML does not conform to the schema | Review the file against the `CompositionSpec` data contract |
| `PersonaNotFound: {id}` | A persona ID in the spec is not in the library | Verify the persona directory exists under `personas/` |
| `StackNotFound: {id}` | A stack ID in the spec is not in the library | Verify the stack directory exists under `stacks/` |
| `MissingPersonaFile: {persona}/{file}` | A persona directory is missing a required `.md` file | Ensure `persona.md`, `outputs.md`, and `prompts.md` all exist |
| `OutputDirNotWritable` | Cannot write to the target directory | Check permissions and that parent directories exist |

## Examples

**Compile with defaults:**
```
/compile-team
```
Reads `./ai/team/composition.yml`, compiles all selected personas and stacks, writes output to the configured `output_root/output_folder`.

**Compile a specific composition file:**
```
/compile-team ./configs/web-app-team.yml
```
Uses a custom composition file from a different location.

**Dry run to preview what would be generated:**
```
/compile-team --dry-run --verbose
```
Validates the composition spec, reports all personas and stacks that would be compiled, and lists the files that would be written -- without actually writing anything.

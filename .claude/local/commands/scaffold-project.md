# /scaffold-project Command

Claude Code slash command that creates a new project folder structure from a composition spec.

## Purpose

Set up the complete repo skeleton for a Foundry-generated project. This creates the directory structure, CLAUDE.md, agent wrappers, context documents, and output folders that all personas and skills operate within. Run this before `/compile-team` and `/seed-tasks`.

## Usage

```
/scaffold-project [composition-file] [--output <path>]
```

- `composition-file` -- Path to a `composition.yml` file. Defaults to `./ai/team/composition.yml` if omitted.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Composition spec | `composition.yml` (YAML) | Yes |
| Output directory | `--output` flag or from composition spec | No |

## Process

1. **Load composition spec** -- Parse the YAML and validate against the CompositionSpec schema.
2. **Create directories** -- Build the full `.claude/` and `ai/` directory tree.
3. **Generate files** -- Write CLAUDE.md, README.md, agent wrappers, context docs, and composition snapshot.
4. **Create output folders** -- Set up `ai/outputs/{persona}/` with READMEs for each team member.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Project constitution | `CLAUDE.md` | Team overview and project structure |
| Agent wrappers | `.claude/agents/{persona}.md` | One per active persona |
| Project context | `ai/context/project.md` | Stacks, personas, hooks, responsibilities |
| Composition snapshot | `ai/team/composition.yml` | Copy of the input spec |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--output <path>` | From composition spec | Override the output directory |
| `--force` | `false` | Overwrite existing files in the output directory |
| `--dry-run` | `false` | Show what would be created without writing files |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `CompositionFileNotFound` | The specified composition file does not exist | Check the path; default is `./ai/team/composition.yml` |
| `InvalidCompositionSpec` | YAML does not conform to the schema | Review the file against the CompositionSpec data contract |
| `OutputDirNotWritable` | Cannot write to the target directory | Check permissions and that parent directories exist |

## Examples

**Scaffold with defaults:**
```
/scaffold-project
```
Reads `./ai/team/composition.yml` and creates the project structure at the configured output root.

**Scaffold from a specific composition:**
```
/scaffold-project examples/small-python-team.yml --output ./my-project
```
Creates the project structure at `./my-project/` using the specified composition.

**Preview without writing:**
```
/scaffold-project --dry-run
```
Shows the files and directories that would be created without writing anything.

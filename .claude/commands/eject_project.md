# /eject_project Command

Copies a harvested project from its temp directory to a permanent location as a sibling of this repo, then initializes git.

## Usage

```
/eject_project [project-name] [--from <harvest-output-dir>]
```

- `project-name` -- Name of the project to eject. Matched against `/tmp/harvest-<name>/` directories. Also used as the target folder name.
- `--from <path>` -- Override the source directory instead of scanning `/tmp/harvest-*/`.

## Process

1. **Find harvest outputs** -- Scan `/tmp/harvest-*/project-folder/` for available harvested projects. If `--from <path>` is provided, use that path directly instead of scanning.

2. **Select project** -- If `project-name` is provided as an argument, match it against discovered harvest directories (e.g., `express` matches `/tmp/harvest-express/`). If no argument is given, list all available harvests and ask the user to pick one.

3. **Determine target** -- The target directory is a sibling of this repo's root. Compute it as `<repomirrorkit-parent>/<project-name>/`. For example, if this repo is at `/home/gregg/workspace/personal/repomirrorkit`, the target for project `express` would be `/home/gregg/workspace/personal/express/`.

4. **Guard against overwrites** -- If the target directory already exists, warn the user and ask for explicit confirmation before proceeding. Show the full target path in the warning.

5. **Copy** -- Copy the entire contents of the `project-folder/` directory to the target:
   ```
   cp -r /tmp/harvest-<name>/project-folder/. <target>/
   ```
   Use `/.` to copy contents without nesting the `project-folder` directory itself.

6. **Initialize git** -- Run `git init` in the new target directory so it starts as a proper git repository.

7. **Confirm** -- Display:
   - The full target path
   - File count (use `find <target> -type f | wc -l`)
   - A hint: `cd <target>` to start working in the new project

## Examples

**Eject by name:**
```
/eject_project express
```
Copies `/tmp/harvest-express/project-folder/` to `../express/` (relative to this repo), runs `git init`, reports success.

**List and pick:**
```
/eject_project
```
Scans `/tmp/harvest-*/`, lists available projects, asks user to choose.

**Eject from custom path:**
```
/eject_project myapp --from /tmp/custom-output
```
Copies `/tmp/custom-output/project-folder/` to `../myapp/`.

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No harvests found | No `/tmp/harvest-*/project-folder/` directories exist | Run the harvester first to generate a project |
| No match | The given project name doesn't match any harvest directory | Check available harvests with `/eject_project` (no args) |
| Target exists | The sibling directory already exists | User must confirm overwrite or choose a different name |
| Copy failed | Permission or disk space issue | Check permissions on the parent directory and available disk space |
| Source has no project-folder | The harvest dir exists but has no `project-folder/` subdirectory | The harvest may be incomplete — re-run the harvester |

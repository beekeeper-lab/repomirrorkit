# /docs-update Command

Audits project documentation against the live codebase and fixes stale values. All facts are gathered by introspection (shell commands, file scans) — nothing is hardcoded.

## Usage

```
/docs-update [--dry-run]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | `false` | Audit only — display `[OK]` / `[STALE]` / `[MISSING]` report without writing changes |

## Process

1. **Discover** — Collect live facts: test count, module lists, wizard pages, bean totals, skill/command counts, git log for changelog, directory tree
2. **Audit** — Compare each fact against its doc location. Print a checklist of `[OK]`, `[STALE]`, or `[MISSING]` findings. Stop here if `--dry-run`.
3. **Update** — Fix every stale finding. Regenerate module maps and directory trees from scratch (not patched).
4. **Verify** — Re-run audit checks on updated files. All must return `[OK]`.
5. **Commit** — Single atomic commit with all doc changes.

## Documents Checked

| Document | What Is Checked |
|----------|----------------|
| `CLAUDE.md` | Test count in repo structure comment |
| `README.md` | Project structure tree, wizard page count, command tables |
| `ai/context/project.md` | Module map, test count, wizard page count |
| `CHANGELOG.md` | `[Unreleased]` section for beans completed since last release |
| `MEMORY.md` | Test count and module count in Current Status |

## Error Handling

| Error | Resolution |
|-------|------------|
| `pytest --collect-only` fails | Report error, skip test-count checks |
| Protected path in write set | Abort — never modifies `ai-team-library/`, `ai/beans/` contents, or `ai/outputs/` |
| Verify phase has failures | Report which checks still fail, do not commit |

## Examples

**Audit without changing anything:**
```
/docs-update --dry-run
```

**Fix all stale docs and commit:**
```
/docs-update
```

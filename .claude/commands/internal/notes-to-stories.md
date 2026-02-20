# /notes-to-stories Command

Claude Code slash command that converts unstructured notes into user stories with acceptance criteria.

## Purpose

Turn meeting notes, feature requests, brainstorming output, or any unstructured text into properly formatted user stories. Each story gets testable acceptance criteria, open questions are flagged, and risks are identified. This is the starting point for a delivery cycle -- raw ideas go in, structured backlog items come out.

## Usage

```
/notes-to-stories <notes-file-or-text> [--template <path>] [--existing <dir>]
```

- `notes-file-or-text` -- Path to a file containing raw notes, or inline text.

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Raw notes | File path or inline text | Yes |
| Story template | `--template` flag or default BA template | No |
| Existing stories | `--existing` flag or `ai/outputs/ba/` | No |

## Process

1. **Parse raw input** -- Identify distinct features, requests, and action items.
2. **Draft stories** -- Create user stories in "As a / I want / So that" format.
3. **Add acceptance criteria** -- Write testable, binary pass/fail criteria for each story.
4. **Flag open questions and risks** -- Surface ambiguities and technical risks.
5. **Deduplicate** -- Check against existing stories if available.
6. **Write output** -- Produce individual story files and a summary.

## Output

| Artifact | Path | Description |
|----------|------|-------------|
| Story files | `ai/outputs/ba/user-stories/` | One markdown file per story |
| Summary | `ai/outputs/ba/story-summary.md` | Overview with all stories, questions, and risks |

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--template <path>` | BA persona template | Custom story template to use |
| `--existing <dir>` | `ai/outputs/ba/` | Directory of existing stories for deduplication |
| `--output <dir>` | `ai/outputs/ba/user-stories/` | Override the output directory |
| `--format <brief\|full>` | `full` | `brief` produces inline stories; `full` produces individual files |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `EmptyInput` | Notes are empty or contain no actionable content | Provide substantive notes |
| `TemplateNotFound` | Template path does not exist | Check the path or omit to use the default |

## Examples

**Convert meeting notes:**
```
/notes-to-stories meeting-notes-2025-01-15.md
```
Reads the notes file and produces structured stories in `ai/outputs/ba/user-stories/`.

**Inline text:**
```
/notes-to-stories "Users need password reset flow, admin dashboard with metrics, and email notifications for order status changes"
```
Converts the inline text into three user stories with acceptance criteria.

**With deduplication:**
```
/notes-to-stories sprint-planning.md --existing ai/outputs/ba/user-stories/
```
Produces new stories while flagging any that overlap with existing backlog items.

# /trello-add Command

Creates a Trello card from the command line. First line of text becomes the card name; remaining lines become the description.

## Usage

```
/trello-add <text>                     # Create card in Backlog
/trello-add --sprint <text>            # Create card in Sprint_Backlog
/trello-add --label <color> <text>     # Create card with a label
/trello-add --sprint --label red <text> # Both flags
```

## Examples

| Command | Result |
|---------|--------|
| `/trello-add Fix validator error` | Card "Fix validator error" in Backlog |
| `/trello-add --sprint Urgent hotfix` | Card "Urgent hotfix" in Sprint_Backlog |
| `/trello-add --label red Pipeline broken` | Card "Pipeline broken" with red label in Backlog |

## Process

1. Parse flags (`--sprint`, `--label <color>`) and split remaining text into name + description
2. Find the Foundry board and target list (Backlog or Sprint_Backlog)
3. Resolve label color if requested
4. Create the card and print its URL

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--sprint` | off | Route card to Sprint_Backlog instead of Backlog |
| `--label <color>` | none | Apply a board label by color (red, green, blue, yellow, etc.) |

## Error Handling

| Error | Resolution |
|-------|------------|
| No text provided | Report error with usage hint |
| List not found | Show available list names |
| Label color not found | Warn and create card without label |

# Skill: Notes to Stories

## Description

Transforms unstructured input -- meeting notes, brainstorming dumps, feature
requests, Slack threads, or plain-language descriptions -- into structured user
stories with acceptance criteria, open questions, and identified risks. This
skill is the BA persona's primary tool for converting raw requirements into
actionable backlog items that the rest of the team can work from.

## Trigger

- Invoked by the `/notes-to-stories` slash command.
- Called by the BA persona during requirements gathering.
- Can be run iteratively as new information surfaces.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| raw_notes | Text or file path | Yes | Unstructured input: meeting notes, feature requests, conversation transcripts |
| project_context | File path | No | `ai/context/project.md` for domain and architectural context; defaults to project's context if available |
| story_template | File path | No | Template for story format; defaults to `personas/ba/templates/user-story.md` |
| existing_stories | Directory path | No | Path to existing stories to avoid duplication; defaults to `ai/outputs/ba/` |

## Process

1. **Parse raw input** -- Read the unstructured notes and identify distinct themes, features, or requests. Separate signal from noise (action items from discussion, decisions from opinions).
2. **Extract candidate stories** -- For each distinct feature or request, draft a user story in the format: "As a [user type], I want [capability], so that [benefit]."
3. **Define acceptance criteria** -- For each story, write testable acceptance criteria. Each criterion must be binary (pass/fail) and specific enough for Tech-QA to verify without ambiguity.
4. **Identify open questions** -- Flag any ambiguity, missing information, or unstated assumptions as explicit open questions. Tag each question with who should answer it (stakeholder, architect, developer).
5. **Assess risks** -- Identify technical risks, dependency risks, or scope risks associated with each story. Rate each as low/medium/high impact.
6. **Deduplicate against existing stories** -- If existing stories are available, check for overlap and flag potential duplicates rather than creating redundant items.
7. **Produce structured output** -- Write each story as a standalone markdown file following the story template. Produce a summary listing all stories, open questions, and risks.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| user_stories | Directory of markdown files | One file per story following the BA story template |
| story_summary | Markdown file | Overview listing all stories with status, open questions, and risks |
| open_questions | Section in summary | Explicit list of unresolved questions with suggested answerers |
| risk_register | Section in summary | Identified risks with impact ratings |

## Quality Criteria

- Every story follows the "As a / I want / So that" format or an equivalent structured format.
- Every story has at least two testable acceptance criteria.
- Acceptance criteria use concrete, measurable language -- no "should work well" or "is user-friendly."
- Every open question identifies who should answer it.
- No story duplicates an existing story in the backlog (when existing stories are provided).
- The summary is self-contained: a reader unfamiliar with the raw notes can understand the full scope.
- Stories are sized for a single work cycle -- epics are split into multiple stories.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `EmptyInput` | Raw notes are empty or contain no actionable content | Provide substantive meeting notes or requirements |
| `TemplateNotFound` | The story template path does not exist | Check the template path or use the default BA template |
| `ExistingStoriesUnreadable` | Cannot parse files in the existing stories directory | Verify the file format in the stories directory |
| `AmbiguousScope` | Notes describe conflicting or contradictory requirements | Flag the conflicts as open questions; do not guess resolution |

## Dependencies

- BA persona's story template (`personas/ba/templates/user-story.md`)
- Project context (`ai/context/project.md`) for domain understanding
- No other skills are required before this one; it is typically the first step in a delivery cycle

# Skill: Handoff

## Description

Creates a structured handoff packet when one persona completes their phase and
the next persona needs to pick up. The packet bundles everything the receiving
persona needs: what was produced, where to find it, what decisions were made,
what assumptions were baked in, and what the receiver should do next. This
skill bridges the gap between close-loop (which verifies completion) and the
next persona's work start — it is the "baton pass" that prevents context loss
between roles in the dependency wave.

## Trigger

- Invoked by the `/handoff` slash command.
- Called by any persona when their phase of work is complete and a downstream persona needs to begin.
- Automatically suggested by the close-loop skill when a task passes verification and has downstream dependents.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| from_persona | String | Yes | The persona handing off (e.g., "architect") |
| to_persona | String | Yes | The persona receiving the handoff (e.g., "developer") |
| work_id | String | No | Work item ID this handoff relates to (e.g., "WRK-003") |
| artifacts | List of file paths | No | Explicit list of artifacts to include; auto-detected from the persona's output directory if omitted |
| notes | Text | No | Free-form context the sender wants to communicate beyond what's in the artifacts |

## Process

1. **Identify the handing-off persona's outputs** -- If artifacts are not explicitly listed, scan `ai/outputs/{from_persona}/` for files modified during the current work cycle. Include all deliverables: specs, ADRs, stories, test plans, review reports, etc.
2. **Summarize what was produced** -- For each artifact, extract a one-line summary: file path, what it contains, and its status (draft, reviewed, approved).
3. **Capture decisions made** -- Scan the artifacts and ADR directory for decisions made during this phase. List each decision with a one-line summary and a link to the full record.
4. **Document assumptions** -- Identify assumptions baked into the work that the receiving persona should be aware of. These are things the sender assumed to be true but did not formally verify — the receiver may need to validate them.
5. **Define what the receiver should do** -- Based on the dependency wave and the work type, list the specific tasks or objectives the receiving persona should tackle. Reference the relevant task specs or seeded tasks.
6. **Flag risks and open questions** -- List anything unresolved that the receiver should be aware of: known risks, open questions from the BA, untested assumptions, or deferred items.
7. **Identify key files** -- Create a "start here" section listing the 2-3 most important files the receiver should read first, in order.
8. **Write handoff packet** -- Save the structured handoff as `ai/handoffs/{from}-to-{to}-{work_id}.md`.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| handoff_packet | Markdown file | Structured handoff document with artifacts, decisions, assumptions, next steps, and risks |

## Quality Criteria

- The handoff packet is self-contained: the receiving persona can start work without asking the sender clarifying questions.
- Every artifact is referenced by its exact file path, not vague descriptions.
- The "start here" section contains no more than three files and guides the receiver to the most critical context first.
- Decisions are linked to their source (ADR or decision record), not restated in full.
- Assumptions are explicitly labeled as assumptions, not stated as facts.
- Open questions identify who should answer them (if known).
- The handoff includes the work ID so it can be traced back to the originating work item.
- The receiving persona's expected outputs are stated so they know what "done" looks like for their phase.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `FromPersonaNotFound` | The handing-off persona is not in the team composition | Check the persona ID against the composition spec |
| `ToPersonaNotFound` | The receiving persona is not in the team composition | Check the persona ID against the composition spec |
| `NoArtifactsFound` | No artifacts found in the sender's output directory | Verify the persona has produced outputs, or list artifacts explicitly |
| `HandoffDirNotWritable` | Cannot write to `ai/handoffs/` | Check permissions or scaffold the project |
| `SamePersona` | From and to persona are the same | A handoff requires two different personas |

## Dependencies

- **Close Loop** skill (typically runs before handoff to verify the sender's work is complete)
- **Seed Tasks** or **New Work** skill (task specs provide context for what the receiver should do)
- Sender persona's output directory (`ai/outputs/{from_persona}/`)
- Composition spec for validating persona IDs
- ADR directory for capturing decisions made during the phase

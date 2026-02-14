# Content Style Guide

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | [YYYY-MM-DD]                   |
| Owner         | [guide author]                 |
| Related links | [issue/PR/ADR URLs]            |
| Status        | Draft / Reviewed / Approved    |

## Voice and Tone

*Describe how the product communicates with users. Voice is consistent; tone adapts to context.*

- **Voice:** [e.g., "Professional but approachable. We explain things clearly without jargon."]
- **Tone when guiding:** [e.g., "Encouraging and supportive"]
- **Tone when reporting errors:** [e.g., "Calm, specific, and solution-oriented"]
- **Tone when confirming success:** [e.g., "Brief and positive"]

## Terminology

*Maintain consistent vocabulary across the product. Add rows as the product evolves.*

| Preferred Term    | Avoid               | Reason                                     |
|-------------------|----------------------|--------------------------------------------|
| [correct term]    | [incorrect variant]  | [why the preferred term is better]         |
| [correct term]    | [incorrect variant]  | [why the preferred term is better]         |

## UI Label Conventions

*Rules for labeling buttons, menus, fields, and headings.*

- **Buttons:** [e.g., "Use verb phrases: Save changes, Create project, Send invite"]
- **Menu items:** [e.g., "Use noun phrases or short verb phrases: Settings, Export data"]
- **Form field labels:** [e.g., "Use sentence case, no trailing colon"]
- **Page headings:** [e.g., "Use title case for top-level headings, sentence case for subheadings"]
- **Links:** [e.g., "Describe the destination, never use 'click here'"]

## Error Message Patterns

*Follow a consistent structure so users understand what happened and what to do.*

- **Format:** [e.g., "State what went wrong, then what to do. Keep under 2 sentences."]
- **Tone:** [e.g., "Neutral and helpful. Never blame the user."]

| Scenario                     | Example Message                                       |
|------------------------------|-------------------------------------------------------|
| Required field missing       | [e.g., "Name is required."]                           |
| Invalid format               | [e.g., "Enter a valid email address."]                |
| System/server error          | [e.g., "Something went wrong. Try again in a moment."]|
| Permission denied            | [e.g., "You don't have access. Contact your admin."]  |

## Empty State Messages

*Guide users when there is nothing to display yet.*

- **Pattern:** [e.g., "Explain what will appear here and how to get started."]
- **Example:** [e.g., "No projects yet. Create your first project to get started."]

## Confirmation Dialogs

*Use when the user is about to take a significant or irreversible action.*

- **Title:** [e.g., "Verb + object: Delete project"]
- **Body:** [e.g., "State the consequence clearly: This will permanently remove the project and all its data."]
- **Primary action label:** [e.g., "Match the title verb: Delete"]
- **Cancel label:** [e.g., "Cancel"]

## Notification Messages

| Type     | Purpose                    | Example                                       |
|----------|----------------------------|-----------------------------------------------|
| Success  | Confirm completed action   | [e.g., "Changes saved."]                      |
| Info     | Neutral status update      | [e.g., "Your export is being prepared."]       |
| Warning  | Caution before consequence | [e.g., "This action affects all team members."]|
| Error    | Something failed           | [e.g., "Could not save. Check your connection."]|

## Formatting Conventions

| Element          | Convention                                         |
|------------------|----------------------------------------------------|
| Dates            | [e.g., "YYYY-MM-DD or user-locale-aware format"]   |
| Times            | [e.g., "24-hour or 12-hour with AM/PM"]            |
| Numbers          | [e.g., "Use thousands separator for values > 999"] |
| Currency         | [e.g., "Symbol before number, two decimal places"] |
| Capitalization   | [e.g., "Sentence case for UI text, Title Case for page headings"] |

## Placeholder Text Conventions

- **Input fields:** [e.g., "Show a realistic example: jane.doe@example.com"]
- **Search fields:** [e.g., "Describe what can be searched: Search by name or email"]
- **Avoid:** [e.g., "Do not use placeholder text as a substitute for labels"]

## Definition of Done

- [ ] Voice and tone documented with contextual examples
- [ ] Terminology table reviewed by product and engineering
- [ ] Error message patterns validated against existing UI
- [ ] Formatting conventions align with localization strategy
- [ ] Guide reviewed by at least one non-designer for clarity

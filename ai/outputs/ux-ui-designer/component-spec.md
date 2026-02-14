# Component Spec

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | [YYYY-MM-DD]                   |
| Owner         | [spec author]                  |
| Related links | [issue/PR/ADR URLs]            |
| Status        | Draft / Reviewed / Approved    |

## Component Overview

- **Component name:** [PascalCase name, e.g., "StatusBadge"]
- **Purpose:** [one-sentence description of what this component does]
- **Usage context:** [where this component appears in the UI]

## Props / Inputs

*Define every configurable property the component accepts.*

| Name          | Type          | Required | Default   | Description                        |
|---------------|---------------|----------|-----------|------------------------------------|
| [prop name]   | [data type]   | Yes / No | [value]   | [what this prop controls]          |
| [prop name]   | [data type]   | Yes / No | [value]   | [what this prop controls]          |
| [prop name]   | [data type]   | Yes / No | [value]   | [what this prop controls]          |

## States

*List every visual state the component can be in.*

| State Name    | Description                     | Visual Indicators                  |
|---------------|---------------------------------|------------------------------------|
| Default       | [normal resting state]          | [colors, borders, icons]           |
| Hover         | [mouse is over the element]     | [visual change description]        |
| Focus         | [element has keyboard focus]    | [focus ring, outline, highlight]   |
| Active        | [element is being pressed]      | [visual change description]        |
| Disabled      | [element is not interactive]    | [muted colors, cursor style]       |
| Loading       | [awaiting data or action]       | [spinner, skeleton, placeholder]   |
| Error         | [invalid or failed state]       | [color, icon, message]             |

## Behavior

*Describe how the component responds to user interaction.*

### Click / Tap
[What happens when the user clicks or taps the component]

### Hover
[Any tooltip, preview, or visual feedback on hover]

### Focus and Keyboard Navigation
[Tab order behavior, keyboard shortcuts, Enter/Space activation]

### Drag (if applicable)
[Drag behavior, drop targets, visual feedback during drag]

## Accessibility Requirements

*Ensure the component is usable by everyone.*

| Requirement               | Specification                                   |
|---------------------------|-------------------------------------------------|
| Role                      | [ARIA role, e.g., button, alert, dialog]        |
| ARIA attributes           | [aria-label, aria-describedby, aria-expanded]   |
| Keyboard navigation       | [which keys do what]                            |
| Screen reader announcement| [what is read aloud on focus/state change]      |
| Minimum contrast ratio    | [4.5:1 for text, 3:1 for large text/graphics]  |

## Content

*Define all text the component may display.*

| Content Type      | Value / Pattern                                  |
|-------------------|--------------------------------------------------|
| Label             | [primary label text]                             |
| Placeholder text  | [placeholder if applicable]                      |
| Help text         | [supplementary guidance shown near the element]  |
| Error message(s)  | [specific error text for each validation case]   |
| Empty state text  | [text when no data is present]                   |

## Edge Cases

*Document boundary conditions and unusual scenarios.*

- [What happens with very long text content]
- [Behavior at minimum/maximum values]
- [Behavior when required data is missing]
- [How the component responds to rapid repeated interaction]

## Definition of Done

- [ ] All props documented with types and defaults
- [ ] Every state has visual indicator described
- [ ] Keyboard interactions specified
- [ ] ARIA roles and attributes defined
- [ ] Error messages and edge cases covered
- [ ] Reviewed by developer and accessibility lead

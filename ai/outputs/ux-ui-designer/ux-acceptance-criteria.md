# UX Acceptance Criteria

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | [YYYY-MM-DD]                   |
| Owner         | [criteria author]              |
| Related links | [issue/PR/ADR URLs]            |
| Status        | Draft / Reviewed / Approved    |

## Feature / Story Reference

- **Feature name:** [name]
- **Story or ticket:** [identifier]
- **Related wireframe / flow:** [link or document name]

## Interaction Criteria

*Verify that the system responds correctly to user actions.*

| ID    | When the user...              | The system should...                | Within / Notes          |
|-------|-------------------------------|-------------------------------------|-------------------------|
| IX-01 | [performs action]             | [expected response]                 | [timing or constraint]  |
| IX-02 | [performs action]             | [expected response]                 | [timing or constraint]  |
| IX-03 | [performs action]             | [expected response]                 | [timing or constraint]  |

## Visual Criteria

*Verify that elements appear correctly in each state.*

| ID    | Element                | State           | Expected Appearance                      |
|-------|------------------------|-----------------|------------------------------------------|
| VZ-01 | [element name]         | [state]         | [colors, size, position, typography]     |
| VZ-02 | [element name]         | [state]         | [colors, size, position, typography]     |
| VZ-03 | [element name]         | [state]         | [colors, size, position, typography]     |

## Accessibility Criteria

*Verify that the feature is usable by all users regardless of ability.*

| ID    | Requirement                                                        | Pass/Fail |
|-------|--------------------------------------------------------------------|-----------|
| AC-01 | Component is fully operable via keyboard (Tab, Enter, Space, Esc)  | [ ]       |
| AC-02 | Focus order is logical and visible                                  | [ ]       |
| AC-03 | Screen reader announces component role, name, and state changes     | [ ]       |
| AC-04 | Color contrast meets WCAG AA minimum (4.5:1 text, 3:1 non-text)   | [ ]       |
| AC-05 | Interactive targets meet minimum size (44x44 CSS pixels)            | [ ]       |

## Content Criteria

*Verify that text content matches the spec and follows the style guide.*

| ID    | Element              | Expected Content                          | Follows Style Guide |
|-------|----------------------|-------------------------------------------|---------------------|
| CT-01 | [label/heading/msg]  | [exact text or pattern]                   | Yes / No            |
| CT-02 | [label/heading/msg]  | [exact text or pattern]                   | Yes / No            |
| CT-03 | [error message]      | [exact text or pattern]                   | Yes / No            |

## Responsive Behavior

*Verify the feature works across target viewport sizes.*

| ID    | Viewport            | Expected Behavior                                   |
|-------|---------------------|-----------------------------------------------------|
| RS-01 | [e.g., >= 1024px]   | [layout and behavior at this size]                  |
| RS-02 | [e.g., 768-1023px]  | [layout and behavior at this size]                  |
| RS-03 | [e.g., < 768px]     | [layout and behavior at this size]                  |

## Edge Cases

*Verify behavior under boundary or unusual conditions.*

| ID    | Scenario                        | Expected Behavior                         |
|-------|---------------------------------|-------------------------------------------|
| EC-01 | [edge case description]         | [what should happen]                      |
| EC-02 | [edge case description]         | [what should happen]                      |

## Definition of Done

- [ ] All interaction criteria verified in a working build
- [ ] Visual criteria matched against design spec or wireframe
- [ ] Accessibility criteria tested with keyboard and screen reader
- [ ] Content reviewed against style guide
- [ ] Responsive behavior verified at all target breakpoints
- [ ] Edge cases tested and passing

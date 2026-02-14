# Textual Wireframe

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | [YYYY-MM-DD]                   |
| Owner         | [wireframe author]             |
| Related links | [issue/PR/ADR URLs]            |
| Status        | Draft / Reviewed / Approved    |

## Screen Overview

- **Screen name:** [unique screen identifier]
- **Purpose:** [what this screen allows the user to do]
- **Route/URL pattern:** [e.g., /settings/profile]

## Layout Description

*Describe the spatial arrangement of the screen from top to bottom. Use plain language -- no tool-specific notation required.*

### Header
[Describe header contents: logo placement, navigation items, user menu, search bar, etc.]

### Main Content Area
[Describe the primary content: forms, lists, cards, data displays, calls to action, etc.]

### Sidebar (if applicable)
[Describe sidebar contents: filters, secondary navigation, contextual help, etc.]

### Footer
[Describe footer contents: links, copyright, support info, etc.]

## Elements

*List every interactive and informational element on the screen.*

| Element             | Type        | Content / Label        | Behavior on Interaction         |
|---------------------|-------------|------------------------|---------------------------------|
| [element name]      | [button / input / link / dropdown / toggle / display] | [visible text or label] | [what happens on click/change] |
| [element name]      | [type]      | [content]              | [behavior]                      |
| [element name]      | [type]      | [content]              | [behavior]                      |

## States

*Describe how the screen appears under each condition.*

| State    | Description                                                   |
|----------|---------------------------------------------------------------|
| Default  | [what the user sees on initial load with typical data]        |
| Loading  | [what appears while data is being fetched]                    |
| Empty    | [what appears when there is no data to display]               |
| Error    | [what appears when a system error occurs]                     |
| Success  | [what appears after a successful action, if applicable]       |

## Navigation

*Describe how users arrive at and leave this screen.*

- **Reached from:** [screen name(s) or action(s) that lead here]
- **Leads to:** [screen name(s) the user can navigate to from here]
- **Back behavior:** [what happens when user navigates back]

## Notes

- [Design constraint, open question, or assumption]

## Definition of Done

- [ ] All interactive elements listed with behaviors
- [ ] All states described (default, loading, empty, error, success)
- [ ] Navigation paths documented (inbound and outbound)
- [ ] Layout reviewed against user flow
- [ ] Accessibility notes captured for non-standard elements

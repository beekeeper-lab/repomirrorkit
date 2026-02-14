# Accessibility Checklist

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | [YYYY-MM-DD]                   |
| Owner         | [checklist author]             |
| Related links | [issue/PR/ADR URLs]            |
| Status        | Draft / Reviewed / Approved    |

## Scope

*Identify what is being evaluated.*

- **Feature / screen / component:** [name]
- **Target conformance level:** [e.g., WCAG 2.1 AA]

## Perceivable

*Users must be able to perceive all information and UI components.*

- [ ] All images and icons have meaningful alt text (or are marked decorative)
- [ ] Color is not the sole means of conveying information (e.g., status, errors)
- [ ] Text and interactive elements meet minimum contrast ratio (4.5:1 normal text, 3:1 large text)
- [ ] Non-text contrast meets 3:1 for UI components and graphical objects
- [ ] Text can be resized up to 200% without loss of content or functionality
- [ ] Content reflows properly at 320px viewport width (no horizontal scrolling)
- [ ] Audio and video content has captions or transcripts where applicable
- [ ] No content flashes more than three times per second

## Operable

*Users must be able to operate all UI components and navigation.*

- [ ] All interactive elements are reachable and operable via keyboard alone
- [ ] Focus indicator is visible on every focusable element
- [ ] No keyboard traps -- users can move focus away from every element
- [ ] Skip-to-content link is present on pages with repeated navigation
- [ ] Focus order follows a logical reading sequence
- [ ] Touch targets are at least 44x44 CSS pixels
- [ ] Time limits can be extended, adjusted, or turned off (if any exist)
- [ ] Users can pause, stop, or hide any moving or auto-updating content

## Understandable

*Content and interface behavior must be predictable and comprehensible.*

- [ ] Page language is set in the HTML lang attribute
- [ ] Form fields have visible, associated labels
- [ ] Error messages identify the field and describe how to fix the problem
- [ ] Required fields are indicated before form submission
- [ ] Navigation and naming are consistent across pages
- [ ] Instructions do not rely solely on shape, size, or visual location

## Robust

*Content must be compatible with current and future assistive technologies.*

- [ ] HTML is valid and well-structured (proper heading hierarchy, landmarks)
- [ ] ARIA roles, states, and properties are used correctly and only when needed
- [ ] Custom components expose name, role, and value to assistive technology
- [ ] Tested with at least one screen reader (specify: [screen reader name])
- [ ] Tested with keyboard-only navigation
- [ ] Tested with browser zoom at 200%

## Issues Found

*Log any failures discovered during evaluation.*

| Issue | Criterion      | Severity    | Element / Location | Remediation              |
|-------|----------------|-------------|--------------------|--------------------------|
| 1     | [WCAG ref]     | High/Med/Low| [where it occurs]  | [how to fix it]          |
| 2     | [WCAG ref]     | High/Med/Low| [where it occurs]  | [how to fix it]          |

## Definition of Done

- [ ] All checklist items evaluated and marked pass or fail
- [ ] Failing items logged in issues table with remediation plan
- [ ] High-severity issues resolved before release
- [ ] Re-test completed after fixes are applied
- [ ] Results shared with development team and stakeholders

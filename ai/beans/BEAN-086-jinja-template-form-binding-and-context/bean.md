# BEAN-086: Jinja/Template Form Binding and Context Tracing

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-086 |
| **Status** | Unapproved |
| **Priority** | Medium |
| **Created** | 2026-11-11 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

HTML templates render forms via macros (`wtf.quick_form(form)`) or hand-written inputs whose values come from the view's `render_template(..., form=form)` context. Template screens (`user.html`, `edit_profile.html`) therefore show no fields or actions even though the form class and route are known.

## Goal

Trace `render_template(name, **ctx)` from route handlers to templates, attach the form class/fields and context variables to the template's screen, and merge with the WTForms screen so each page is one screen.

## Acceptance Criteria

- [ ] Each microblog page template maps to one screen carrying its form fields
- [ ] Duplicate form-vs-template screens are merged
- [ ] Navigation edges from `url_for` links resolve to routes
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: real-world triage of the microblog app (`docs/real-world-triage-microblog.md`), 2026-11-11.

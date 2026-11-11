# BEAN-090: HTML Page Routes as First-Class Surfaces (render_template/redirect responses)

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-090 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-11-11 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Server-rendered apps (Flask/Jinja, Django, Rails, Razor) expose *pages*, not JSON APIs. Today every route is an `ApiSurface` whose response is `unknown` (microblog: api_response_contracts 8.6%). A rebuild agent needs to know a route renders template X, redirects to route Y on success, and which context data it passes.

## Goal

Classify routes returning `render_template`/`redirect`/`TemplateResponse`/`View()` as page routes: capture template, redirect targets (`url_for` → resolved route), template context keys, and the form(s) used; keep API semantics for JSON routes.

## Acceptance Criteria

- [ ] Microblog fixture: >=80% of routes have a typed response (json, html+template, or redirect+target)
- [ ] Redirect targets resolve to a route surface where possible
- [ ] Fidelity gate `api_response_contracts` counts html/redirect responses as determined
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: real-world triage of the microblog app (`docs/real-world-triage-microblog.md`), 2026-11-11.

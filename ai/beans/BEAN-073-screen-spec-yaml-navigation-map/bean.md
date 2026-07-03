# BEAN-073: Screen Spec YAML + Mermaid Navigation Map

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-073 |
| **Status** | Unapproved |
| **Priority** | High |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

Once BEAN-064 captures screens, fields, and mappings, that data needs a machine-consumable design artifact a rebuild agent can implement screens from — deliberately free of visual styling (colors/themes are explicitly out of scope for recreation). Markdown beans are for humans; the rebuild needs structure.

## Goal

Stage G emits `<out>/screens/<screen>.yaml` (one structured spec per screen: fields, validations, model mappings, actions, navigation) plus `<out>/screens/navigation-map.md` with a Mermaid flowchart of screen-to-screen navigation rendered from the same data.

## Scope

### In Scope
- `generator/screen_specs.py`: `ScreenSurface` → YAML with a documented, versioned schema (`screen`, `route`, `fields[]` with `name/type/required/validation/binds_to`, `actions[]` with `trigger/api/navigates_to`, `navigation[]`)
- YAML schema documented in `docs/` + validated in tests (schema-versioned for forward compat)
- Navigation map: Mermaid `flowchart` of screens as nodes, navigation/actions as edges, entry routes marked
- Unmapped/unknown items carried as explicit `gap:` entries in the YAML
- REQUIREMENTS.md links the screens directory + navigation map

### Out of Scope
- Wireframe/image generation, layout, styling
- Component-tree detail below the field/action level

## Acceptance Criteria

- [ ] Fixture harvest emits one YAML per detected screen, validating against the documented schema
- [ ] Field entries carry model bindings (or explicit gaps) matching BEAN-064's surfaces
- [ ] `navigation-map.md` Mermaid block compiles (syntax test) and its edges match screen navigation targets
- [ ] YAML is deterministic across runs (stable ordering)
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track C
- Wave 3 — hard dep: BEAN-064
- The YAML schema is a contract for rebuild agents — BA/Architect review the field set before implementation

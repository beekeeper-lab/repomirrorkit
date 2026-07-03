# BEAN-064: `ScreenSurface` + Form/Field Extraction + Field→Model Mapping

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-064 |
| **Status** | Unapproved |
| **Priority** | Critical |
| **Created** | 2026-07-03 |
| **Owner** | team-lead |
| **Category** | App |

## Problem Statement

`ComponentSurface` records prop *names* only. Nothing captures what a screen actually is: its form fields (name, input type, required, validation), the actions it exposes, where those fields go (which API call, which model column), or where the screen navigates. This is the core of the stated recreation need ("how many fields are on a form, those field mappings to a database") and it is captured nowhere today.

## Goal

A new `ScreenSurface` capturing, per route-reachable screen: field inventory (name/input-type/required/validation), actions (submit/delete/etc. → API ref), navigation targets, and a best-effort field→model-column mapping chained through the API contract.

## Scope

### In Scope
- `ScreenSurface` dataclass in `surfaces.py`: `screen_name`, `route_ref`, `fields: list[ScreenField]` (`name`, `input_type`, `required`, `validation`, `bound_api_field`, `bound_model_field`), `actions: list[ScreenAction]` (`trigger`, `api_ref`, `navigation_target`), `navigation_targets`
- React/Next extraction (tree-sitter, BEAN-061): JSX `<input>/<select>/<textarea>` + label association; react-hook-form (`register(...)`, resolver schemas) and Formik idioms; controlled-component state fields
- Vue SFC template extraction (`v-model` bindings) — second framework to prove the pattern
- Mapping pass: screen field → request-schema field (name match + form-submission call tracing) → model field (via BEAN-062/063 contracts + `ModelSurface.fields`); every mapping carries `confidence`
- New bean renderer for screens; fixture screens added to `ts-next`
- Wire into Stage C; surface-map + REQUIREMENTS.md sections

### Out of Scope
- Visual characteristics (colors, themes, layout) — explicitly not the goal
- Svelte/Angular (follow-up beans once two frameworks are proven)
- Pixel-level component hierarchy (screens and fields, not DOM trees)

## Acceptance Criteria

- [ ] Harvesting `ts-next` fixture yields ≥1 `ScreenSurface` with a complete field inventory matching the fixture's form
- [ ] At least one field maps end-to-end: screen field → API request field → model column, with confidence recorded
- [ ] Validation rules from react-hook-form/zod resolver appear on the field entries
- [ ] Screen beans render field tables + action/navigation lists
- [ ] Unmappable fields are recorded with `bound_model_field: null` + gap note, never dropped
- [ ] Lint, type-check, and pytest all clean

## Notes

- Source: recreation-grade audit 2026-07-03 (`ROADMAP-RECREATION.md`), Track A — the audit's highest-value new surface
- Wave 2 — hard dep: BEAN-061; soft dep: BEAN-063 (mapping quality improves with populated contracts)
- Feeds BEAN-073 (screen YAML) and BEAN-076 (field-mapping gate)

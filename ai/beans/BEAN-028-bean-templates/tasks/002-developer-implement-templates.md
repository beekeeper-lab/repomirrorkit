# Task 002: Developer — Implement templates.py

**Owner:** Developer
**Status:** Done
**Depends On:** 001

## Objective

Implement all 7 bean template rendering functions in `src/repo_mirror_kit/harvester/beans/templates.py`.

## Deliverables

- `render_bean(surface, bean_id)` — public dispatch
- `render_route_bean(surface, bean_id)` — 8 sections (spec 8.3)
- `render_component_bean(surface, bean_id)` — 6 sections (spec 8.4)
- `render_api_bean(surface, bean_id)` — 8 sections (spec 8.5)
- `render_model_bean(surface, bean_id)` — 6 sections (spec 8.6)
- `render_auth_bean(surface, bean_id)` — 4 sections (spec 8.7)
- `render_config_bean(surface, bean_id)` — 4 sections (spec 8.8)
- `render_crosscutting_bean(surface, bean_id)` — concern-specific (spec 8.9)
- `_render_frontmatter(bean_id, type, title, source_refs)` — shared utility

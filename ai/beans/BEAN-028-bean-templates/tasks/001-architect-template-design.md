# Task 001: Architect — Template Structure Design

**Owner:** Architect
**Status:** Done

## Objective

Design the module structure and rendering approach for bean templates.

## Design Decisions

1. **Single module**: `src/repo_mirror_kit/harvester/beans/templates.py`
2. **One render function per bean type**: `render_route_bean()`, `render_component_bean()`, etc.
3. **Common frontmatter function**: `_render_frontmatter()` generates YAML frontmatter from surface data
4. **Pure string rendering**: No template engine dependency — use f-strings and string building
5. **Input**: Each function accepts the corresponding `Surface` subclass + a `bean_id` string
6. **Output**: Each function returns a complete markdown string with YAML frontmatter + body sections
7. **Public dispatch**: `render_bean(surface, bean_id)` dispatches to the correct renderer by `surface_type`

## Frontmatter Schema (Spec 8.2)

```yaml
---
id: BEAN-001
type: page
title: "Home Page"
source_refs:
  - file_path: src/routes.py
    start_line: 10
    end_line: 25
traceability: []
status: draft
---
```

## Acceptance

- Functions are stateless and pure (no side effects)
- Templates accept Surface dataclass instances directly
- All generated beans have `status: draft`

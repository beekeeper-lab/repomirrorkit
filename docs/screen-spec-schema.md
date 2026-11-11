# Screen spec schema (version 1.0)

Emitted by the harvester at `<out>/screens/<screen>.yaml` (BEAN-073). One file per screen; no visual styling is captured. The authoritative machine-readable schema is `SCREEN_SCHEMA` in `src/repo_mirror_kit/harvester/generator/screen_specs.py`; tests validate every generated file against it.

```yaml
schema_version: "1.0"
screen: UserForm                 # screen/component name
route: /users/new                # null when the screen is a shared component
framework: react                 # react | vue | svelte | html-template | unknown
source: app/components/UserForm.tsx
fields:
  - name: name
    input_type: text             # html input type, select, textarea, checkbox, ...
    label: Name                  # '' when none found
    required: true
    validation: [required, minLength=2]   # neutral tokens, see business rules
    binds_to:
      api: "POST /api/users#name"  # API operation + request field it feeds, or null
      model: User.name             # model column it ultimately maps to, or null
      confidence: name-match       # how the binding was derived, or null
    gap: null                    # why a binding is missing, or a note string
actions:
  - trigger: submit (onSubmit)   # what the user/system does
    api: POST /api/users         # operation called, or null
    navigates_to: /              # screen path navigated to afterwards, or null
navigation: [/]                  # all navigation targets (links + programmatic)
uses_components: []              # child components composed by this screen
gaps: ["field 'nickname': no matching API request field"]
```

Compatibility: `schema_version` follows semver; consumers must reject unknown major versions and ignore unknown keys within a known major version. Output is deterministic (sorted screens, fixed key order).

`navigation-map.md` renders the same navigation data as a Mermaid `flowchart TD`.

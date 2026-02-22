# Skill: Threat Model

## Description

Performs a STRIDE-based threat analysis over a system's architecture, producing
a structured threat model with identified threats, risk ratings, mitigations,
and a security test checklist. The skill reads architecture documentation and
context to identify trust boundaries, data flows, and entry points, then
systematically evaluates each for Spoofing, Tampering, Repudiation, Information
Disclosure, Denial of Service, and Elevation of Privilege risks. This is the
Security Engineer persona's primary analytical tool.

## Trigger

- Invoked by the `/threat-model` slash command.
- Called by the Security Engineer persona after architecture is defined.
- Should be re-run when architecture changes significantly.

## Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| architecture_doc | File path | Yes | Architecture spec, design doc, or ADR describing the system |
| project_context | File path | No | `ai/context/project.md` for stack and domain context; defaults to project's context |
| scope | String | No | Limit analysis to a specific component or boundary (e.g., "API layer", "auth subsystem") |
| existing_model | File path | No | Previous threat model to update incrementally |

## Process

1. **Parse architecture documentation** -- Extract system components, data stores, external services, user types, and communication channels from the architecture doc.
2. **Identify trust boundaries** -- Map where trust levels change: external-to-internal, user-to-admin, service-to-service, network boundaries.
3. **Map data flows** -- Document what data moves across each trust boundary, its sensitivity classification, and the transport mechanism.
4. **Apply STRIDE per boundary** -- For each trust boundary and data flow, systematically evaluate:
   - **S**poofing: Can an attacker impersonate a legitimate actor?
   - **T**ampering: Can data be modified in transit or at rest?
   - **R**epudiation: Can actions be performed without accountability?
   - **I**nformation Disclosure: Can sensitive data be exposed?
   - **D**enial of Service: Can availability be degraded?
   - **E**levation of Privilege: Can an attacker gain unauthorized access?
5. **Rate each threat** -- Assign risk level (Critical/High/Medium/Low) based on impact and likelihood. Use the project's hooks posture to calibrate: regulated projects have lower risk tolerance.
6. **Define mitigations** -- For each Medium+ threat, propose a specific mitigation with implementation guidance. Reference stack-specific security practices where applicable.
7. **Generate security test checklist** -- Produce testable verification items for each mitigation so Tech-QA or Security Engineer can confirm the mitigation is effective.
8. **Produce the threat model document** -- Write the complete model following the Security Engineer's template.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| threat_model | Markdown file | Complete STRIDE analysis with threats, ratings, and mitigations |
| security_checklist | Markdown file | Testable verification items for each mitigation |
| threat_summary | Section in model | Executive summary with critical/high threat count and top risks |

## Quality Criteria

- Every trust boundary in the architecture is evaluated against all six STRIDE categories.
- Every threat has a risk rating with stated rationale (not just a label).
- Every Medium, High, or Critical threat has at least one specific mitigation.
- Mitigations are actionable: they reference specific technologies, configurations, or code changes -- not vague advice like "improve security."
- The security test checklist has a 1:1 mapping to mitigations: every mitigation has a verification item.
- The model distinguishes between threats that are mitigated, accepted, or transferred.
- If scope is limited, the model explicitly states what was excluded and why.

## Error Conditions

| Error | Cause | Resolution |
|-------|-------|------------|
| `NoArchitectureDoc` | No architecture document provided or found | Create an architecture spec first; the Architect persona can help |
| `EmptyArchitecture` | Architecture doc exists but has no substantive content | Fill in the architecture document with component descriptions and data flows |
| `ScopeNotFound` | The specified scope does not match any component in the architecture | Check the scope string against component names in the architecture doc |
| `NoTrustBoundaries` | Analysis found no trust boundaries (likely an incomplete architecture) | Ensure the architecture doc describes external interfaces and user interactions |

## Dependencies

- Architecture documentation from the Architect persona
- Security Engineer persona's template (`personas/security-engineer/templates/threat-model.md`) if available
- Project context for stack-specific security guidance
- Hooks posture (from composition spec) to calibrate risk tolerance

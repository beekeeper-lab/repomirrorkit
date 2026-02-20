# RepoMirrorKit

A system for generating Claude Code project folders from reusable building blocks.

**Tech stack:** clean-code, devops, python, python-qt-pyside6, security

---

## Team Roster

| Persona | Agent File | Persona Definition | Output Directory |
|---------|------------|--------------------|------------------|
| Software Architect | `.claude/agents/architect.md` | `ai/personas/architect.md` | `ai/outputs/architect/` |
| Business Analyst | `.claude/agents/ba.md` | `ai/personas/ba.md` | `ai/outputs/ba/` |
| Code Quality Reviewer | `.claude/agents/code-quality-reviewer.md` | `ai/personas/code-quality-reviewer.md` | `ai/outputs/code-quality-reviewer/` |
| Developer | `.claude/agents/developer.md` | `ai/personas/developer.md` | `ai/outputs/developer/` |
| DevOps / Release Engineer | `.claude/agents/devops-release.md` | `ai/personas/devops-release.md` | `ai/outputs/devops-release/` |
| Integrator / Merge Captain | `.claude/agents/integrator-merge-captain.md` | `ai/personas/integrator-merge-captain.md` | `ai/outputs/integrator-merge-captain/` |
| Security Engineer | `.claude/agents/security-engineer.md` | `ai/personas/security-engineer.md` | `ai/outputs/security-engineer/` |
| Team Lead | `.claude/agents/team-lead.md` | `ai/personas/team-lead.md` | `ai/outputs/team-lead/` |
| Tech-QA / Test Engineer | `.claude/agents/tech-qa.md` | `ai/personas/tech-qa.md` | `ai/outputs/tech-qa/` |
| UX / UI Designer | `.claude/agents/ux-ui-designer.md` | `ai/personas/ux-ui-designer.md` | `ai/outputs/ux-ui-designer/` |

---

## Stack Quick Reference

### Python

| Concern              | Default Tool / Approach          |
|----------------------|----------------------------------|
| Python version       | 3.12+ (pin in `.python-version`) |
| Package manager      | `uv`                             |
| Build backend        | `hatchling`                      |
| Formatter / Linter   | `ruff` (replaces black, isort, flake8) |
| Type checker         | `mypy` (strict mode)             |
| Test framework       | `pytest`                         |
| Logging              | `structlog` (structured JSON)    |
| Docstring style      | Google-style                     |
| Layout               | `src/` layout                    |

### PySide6

| Concern              | Default                          |
|----------------------|----------------------------------|
| Qt binding           | PySide6 (official, LGPL-friendly)|
| Pattern              | Model/View + signals/slots       |
| Styling              | QSS stylesheets (not inline)     |
| Layout               | Layout managers (never fixed positioning) |
| Type hints           | All public methods typed, including signal signatures |

Full conventions: **`ai/stacks/python.md`** and **`ai/stacks/pyside6.md`**.

---

## Cross-Cutting Safety Rules

These apply to ALL personas, ALL tasks, without exception.

1. **No secrets in code.** Never hardcode secrets, API keys, credentials, or connection strings in source code, configuration files, logs, or build artifacts. Inject at runtime from a secrets manager.
2. **No PII in logs.** Never log personally identifiable information or sensitive data at any log level. Log redacted identifiers only.
3. **Validate at boundaries.** Validate all external inputs at system boundaries -- user input, API responses, file contents. Do not trust internal assumptions about external data.
4. **Least privilege.** Every component, user, and service account should have the minimum permissions needed. Excess privileges are attack surface.
5. **Secure defaults.** Systems should be secure out of the box. Insecure configurations require explicit, documented opt-in.
6. **No disabled safety checks.** Do not disable security features, linters, pre-commit hooks, or safety checks without explicit documented approval.
7. **Flag sensitive changes.** Any design or code that stores, processes, or transmits PII or sensitive data must be flagged for Security Engineer review.
8. **Dependency discipline.** Adding a new dependency is a deliberate decision. Evaluate maintenance status, license compatibility, and security posture before adding.

---

## Cross-Cutting Quality Rules

These apply to ALL personas, ALL artifacts.

1. **Testability.** Every requirement, acceptance criterion, and behavior must be testable. "Fast" is not a requirement; "p95 response time under 150ms" is.
2. **Traceability.** Every requirement traces back to a stakeholder need. Every acceptance criterion traces forward to a test case. Broken chains must be fixed.
3. **Error handling.** Errors should be visible, not swallowed. Use meaningful error messages. No bare `except:` or silent failure patterns. Use `raise ... from err` to preserve exception chains.
4. **Readability.** Code and documents are read far more often than written. Prefer explicit over clever. If it needs a walkthrough to understand, simplify it.
5. **Small and incremental.** Deliver in thin, vertical slices. Small PRs, small stories, small merges. Big-bang anything is an anti-pattern.
6. **Decisions are recorded.** Every significant decision gets a documented rationale (ADR, dev decision, or inline justification). If it was not written down, it was not decided.
7. **No TODO without tracking.** No TODO comments without a linked issue. If it is worth noting, it is worth tracking.
8. **Convention over configuration.** Follow project conventions. Deviations require an ADR with justification. "I prefer it differently" is not justification.

---

## Workflow Reference

| Resource | Path | Purpose |
|----------|------|---------|
| Bean workflow | `ai/context/bean-workflow.md` | Full lifecycle: creation → decomposition → execution → verification → merge |
| Persona definitions | `ai/personas/<name>.md` | Mission, scope, operating principles, outputs spec, prompt templates |
| Stack conventions | `ai/stacks/python.md`, `ai/stacks/pyside6.md` | Language and framework coding standards |
| Agent files | `.claude/agents/<name>.md` | Project-specific workflows per persona |
| Output templates | `ai/outputs/<persona>/` | Structured templates for each persona's deliverables |
| Skills | `.claude/skills/` | Invokable workflow automations |
| Hooks | `.claude/hooks/` | Pre/post action enforcement policies |
| Decisions | `ai/context/decisions/` | Architecture Decision Records |
| Bean backlog | `ai/beans/_index.md` | Work item index and status tracking |

---

## How Persona Context is Loaded

Persona definitions live in `ai/personas/` and are **not** auto-loaded into every conversation. They are loaded on demand when an agent is activated:

1. The agent file (`.claude/agents/<name>.md`) is loaded when the agent starts
2. The agent file references `ai/personas/<name>.md` for the full persona definition
3. The agent reads the persona file and stack conventions as needed

This keeps the system prompt lean. Only cross-cutting rules (this file) load into every conversation.

---

## Maintenance Note

This file is manually maintained. Do not regenerate with `/compile-team`. Persona definitions extracted from the original compiled CLAUDE.md live in `ai/personas/` and stack conventions in `ai/stacks/`. Edit those files directly for persona or stack changes.

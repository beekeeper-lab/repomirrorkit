# Bean Backlog

## Status Key

| Status | Meaning |
|--------|---------|
| Unapproved | Created, awaiting human review and approval |
| Approved | Reviewed and approved, ready for execution |
| In Progress | Tasks created and execution underway |
| Done | All acceptance criteria met |
| Deferred | Intentionally postponed |

## Categories

| Category | Meaning |
|----------|---------|
| App | Changes to the application — features, services, models, UI, CLI |
| Process | Changes to the AI team workflow — agent instructions, skills, commands, communication patterns |
| Infra | Git workflow, hooks, branch protection, CI/CD, deployment |

## Backlog

| Bean ID | Title | Category | Priority | Status | Owner |
|---------|-------|----------|----------|--------|-------|
| BEAN-001 | Project Scaffold | App | High | Done | team-lead |
| BEAN-002 | Clone Form Window | App | High | Done | team-lead |
| BEAN-003 | Enforce Mandatory Tech QA in Long-Run Skill | Process | High | Done | team-lead |
| BEAN-004 | Harvester Package Setup | App | High | Done | team-lead |
| BEAN-005 | CLI Entry Point & Configuration | App | High | Done | team-lead |
| BEAN-006 | State Management & Resume | App | High | Done | team-lead |
| BEAN-007 | Logging & Progress Heartbeat | App | High | Done | team-lead |
| BEAN-008 | Clone & Normalize (Stage A) | App | High | Done | team-lead |
| BEAN-009 | File Inventory (Stage B) | App | High | Done | team-lead |
| BEAN-010 | Detector Framework | App | High | Done | team-lead |
| BEAN-011 | React Detector | App | High | Done | team-lead |
| BEAN-012 | Next.js Detector | App | High | Done | team-lead |
| BEAN-013 | Vue Detector | App | Medium | Done | team-lead |
| BEAN-014 | Svelte Detector | App | Medium | Done | team-lead |
| BEAN-015 | Node API Detector | App | High | Done | team-lead |
| BEAN-016 | Python API Detector | App | High | Done | team-lead |
| BEAN-017 | .NET API Detector | App | Medium | Done | team-lead |
| BEAN-018 | SQL/ORM Data Detector | App | High | Done | team-lead |
| BEAN-019 | Surface Data Model | App | High | Done | team-lead |
| BEAN-020 | Route & Page Analyzer | App | High | Done | team-lead |
| BEAN-021 | Component Analyzer | App | High | Done | team-lead |
| BEAN-022 | API Endpoint Analyzer | App | High | Done | team-lead |
| BEAN-023 | Model & Entity Analyzer | App | High | Done | team-lead |
| BEAN-024 | Auth & Security Analyzer | App | High | Done | team-lead |
| BEAN-025 | Config & Env Var Analyzer | App | High | Done | team-lead |
| BEAN-026 | Cross-cutting Concerns Analyzer | App | High | Done | team-lead |
| BEAN-027 | Traceability Graph Builder (Stage D) | App | High | Done | team-lead |
| BEAN-028 | Bean Templates | App | High | Done | team-lead |
| BEAN-029 | Bean Writer & Indexer (Stage E) | App | High | Done | team-lead |
| BEAN-030 | Coverage Gates & Gap Analysis (Stage F) | App | High | Done | team-lead |
| BEAN-031 | Surface Map Report | App | High | Done | team-lead |
| BEAN-032 | Pipeline Orchestrator | App | High | Done | team-lead |
| BEAN-033 | Harvest Button & Progress UI | App | High | Done | team-lead |
| BEAN-034 | Dependency & Package Analyzer | App | High | Done | team-lead |
| BEAN-035 | Build & Deploy Config Analyzer | App | High | Done | team-lead |
| BEAN-036 | Test Pattern Analyzer | App | High | Done | team-lead |
| BEAN-037 | CLAUDE.md Generator (Stage G) | App | High | Done | team-lead |
| BEAN-038 | File Coverage Analysis & Uncovered File Detection | App | High | Done | team-lead |
| BEAN-039 | Claude-Kit Health Check | Infra | Medium | Done | team-lead |
| BEAN-040 | Fix Stale Project Framing in Docs | App | Low | Done | team-lead |
| BEAN-041 | Bump Default LLM Model to Sonnet 4.6 | App | Medium | Done | team-lead |
| BEAN-042 | Delete Vestigial `runtime_verify` Package | App | Low | Done | team-lead |
| BEAN-043 | Harden `git clone` Argv (Terminator + URL Scheme) | App | High | Done | team-lead |
| BEAN-044 | CLI URL Validation Parity with GUI | App | High | Done | team-lead |
| BEAN-045 | Drop `--llm-api-key` CLI Flag, Helpful Missing-Key Error | App | High | Done | team-lead |
| BEAN-046 | Mitigate LLM Prompt Injection from Repo Content | App | High | Done | team-lead |
| BEAN-047 | Cloned-Repo Total-Size Cap | App | Medium | Done | team-lead |
| BEAN-048 | Tighten Pipeline Per-Stage Exception Handling | App | Medium | Done | team-lead |
| BEAN-049 | Fix Misleading Pipeline Resume-Skip Branches | App | Medium | Done | team-lead |
| BEAN-050 | Fixture-Repo End-to-End Integration Test | App | High | Done | team-lead |
| BEAN-051 | Generate Top-Level `REQUIREMENTS.md` Aggregator | App | High | Done | team-lead |
| BEAN-052 | Generate `.env.example` from Config Surfaces | App | Medium | Done | team-lead |
| BEAN-053 | Generate `RUNBOOK.md` from Build/Deploy Surfaces | App | Medium | Done | team-lead |
| BEAN-054 | Behavioral-Spec Analyzer (Docstrings + Test Names) | App | High | Done | team-lead |
| BEAN-055 | Data-Model Relationships Report (with Mermaid ER) | App | Medium | Done | team-lead |
| BEAN-056 | LLM Enrichment Default-On with Graceful Missing-Key UX | App | Medium | Done | team-lead |
| BEAN-057 | Split `analyzers/models.py` by Framework (Tracer Bullet) | App | Low | Done | team-lead |
| BEAN-058 | Fix `telemetry-stamp` Hook Path Resolution | Infra | High | Done | team-lead |
| BEAN-059 | Fix `--llm` Flag Doc Drift + Config Default Mismatch | App | Low | Done | team-lead |
| BEAN-060 | Persist Stage Outputs → Real `--resume` | App | High | Unapproved | team-lead |
| BEAN-061 | Tree-sitter Extraction Foundation | App | High | Unapproved | team-lead |
| BEAN-062 | API Contract Extraction — Python (Tracer Bullet) | App | Critical | Done | team-lead |
| BEAN-063 | API Contract Extraction — JS/TS Stacks | App | High | Unapproved | team-lead |
| BEAN-064 | `ScreenSurface` + Form/Field Extraction + Field→Model Mapping | App | Critical | Unapproved | team-lead |
| BEAN-065 | `BusinessRuleSurface` — Validation & Constraint Mining | App | High | Unapproved | team-lead |
| BEAN-066 | `SeedDataSurface` — Enums, Lookups, Fixtures, Migration Seeds | App | Medium | Done | team-lead |
| BEAN-067 | `WorkflowSurface` — Entity State Machines | App | Medium | Unapproved | team-lead |
| BEAN-068 | Agentic Enrichment v2 — Repo-Aware Feature Tracing | App | Critical | Unapproved | team-lead |
| BEAN-069 | Feature Clustering Stage (C3) + `build-manifest.json` | App | High | Unapproved | team-lead |
| BEAN-070 | Framework-Neutral Bean Language + Confidence/Gaps Fields | App | Medium | Done | team-lead |
| BEAN-071 | OpenAPI 3.1 Contract Generator | App | High | Done | team-lead |
| BEAN-072 | DB Design Bundle — SQL DDL + JSON Schema + Seed Data | App | Medium | Unapproved | team-lead |
| BEAN-073 | Screen Spec YAML + Mermaid Navigation Map | App | High | Unapproved | team-lead |
| BEAN-074 | Gherkin `.feature` Generation per Feature Cluster | App | High | Unapproved | team-lead |
| BEAN-075 | Sequence + State Mermaid Diagrams | App | Low | Unapproved | team-lead |
| BEAN-076 | Fidelity Coverage Gates (Recreation-Readiness Metrics) | App | High | Done | team-lead |
| BEAN-077 | Golden Parity Fixtures (Request/Response Captures) | App | Medium | Unapproved | team-lead |
| BEAN-078 | Rebuild Eval Harness — Parity Scoring | App | Critical | Unapproved | team-lead |
| BEAN-079 | Stage G Orchestration-Policy Parameterization + Telemetry | App | Medium | In Progress | team-lead |
| BEAN-080 | `--mirror` Mode + Stage H Cleanup (Delete Source & Git History) | App | High | Done | team-lead |
| BEAN-081 | Verbatim-Rule Bean Templates + Zero-`TODO:` Placeholder Policy | App | High | Done | team-lead |
| BEAN-082 | Exact-Value Extraction — Analyzer Depth + LLM `exact_rules` Contract | App | High | Done | team-lead |
| BEAN-083 | Sensitive Findings — Redact Secrets/PII and Surface to Operator | App | High | Done | team-lead |
| BEAN-084 | Redaction Detector Follow-ups (SSN + base64 False Positive) | App | Low | Unapproved | team-lead |

> BEAN-059–079 originate from the recreation-grade audit (2026-07-03). Sequencing, dependency graph, and parallelism analysis: see `ROADMAP-RECREATION.md` at the repo root.
> BEAN-080–083 originate from the mirror-mode spec (2026-07-11). Phasing, decisions, and mirror acceptance criteria for existing beans: see `SPEC-MIRROR-MODE.md` at the repo root.

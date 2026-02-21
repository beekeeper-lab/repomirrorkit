# BEAN-035: Build & Deploy Config Analyzer

| Field | Value |
|-------|-------|
| **Bean ID** | BEAN-035 |
| **Status** | Approved |
| **Priority** | High |
| **Created** | 2026-02-20 |
| **Started** | — |
| **Completed** | — |
| **Duration** | — |
| **Owner** | (unassigned) |
| **Category** | App |

## Problem Statement

The harvester captures what an application does (routes, APIs, models) but not how it is built, tested, and deployed. Dockerfiles, CI/CD pipelines, build scripts, and infrastructure config define the operational context. Without this, generated requirements describe application behavior but omit the build and deployment topology needed to actually run and ship the system.

## Goal

Implement a build and deploy configuration analyzer that extracts build tooling, CI/CD pipelines, containerization, and infrastructure-as-code definitions, producing `BuildDeploySurface` objects for bean generation.

## Scope

### In Scope
- New surface dataclass: `BuildDeploySurface` with fields for config_type, tool, file_path, stages/steps, and targets
- Add `build_deploy` list to `SurfaceCollection`
- Implement `src/repo_mirror_kit/harvester/analyzers/build_deploy.py`
- Detect and parse:
  - **Containerization**: Dockerfile, docker-compose.yml, .dockerignore
  - **CI/CD**: .github/workflows/*.yml, .gitlab-ci.yml, Jenkinsfile, .circleci/config.yml, azure-pipelines.yml, bitbucket-pipelines.yml
  - **Build tools**: Makefile, justfile, taskfile.yml, package.json scripts, tox.ini, noxfile.py
  - **Infrastructure-as-code**: terraform *.tf, pulumi configs, CloudFormation templates, k8s manifests (deployment.yaml, service.yaml, etc.)
  - **Platform configs**: Procfile, app.yaml (App Engine), fly.toml, render.yaml, vercel.json, netlify.toml
- Extract key metadata: build stages, deployment targets, environment variables referenced, exposed ports, base images
- Bean template renderer for build/deploy beans
- Wire into pipeline Stage C
- Coverage gate and gap query
- Unit tests

### Out of Scope
- Executing builds or deployments
- Validating configuration correctness
- Cloud cost estimation
- Secret scanning within config files (BEAN-024 handles auth/security)
- Multi-environment diff analysis (staging vs production)

## Acceptance Criteria

- [ ] `BuildDeploySurface` dataclass exists with config_type, tool, stages, targets fields
- [ ] `SurfaceCollection.build_deploy` list field exists
- [ ] Detects Dockerfiles and extracts base image, exposed ports, build stages
- [ ] Detects docker-compose files and extracts service definitions
- [ ] Detects GitHub Actions workflows and extracts jobs/steps
- [ ] Detects GitLab CI, Jenkins, CircleCI pipeline configs
- [ ] Detects Makefile/justfile/taskfile targets
- [ ] Detects package.json scripts section
- [ ] Detects Kubernetes manifests and Terraform configs
- [ ] Detects platform deployment configs (Procfile, fly.toml, vercel.json, etc.)
- [ ] Bean template renders build/deploy beans with tool, stages, and targets
- [ ] Coverage gate checks build/deploy coverage (threshold >= 75%)
- [ ] Gap query identifies build/deploy configs without beans
- [ ] Unit tests cover each config type detection
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` all pass

## Tasks

| # | Task | Owner | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Add BuildDeploySurface to surfaces.py and extend SurfaceCollection | Developer | — | Pending |
| 2 | Implement build_deploy.py analyzer | Developer | 1 | Pending |
| 3 | Add bean template renderer for build/deploy | Developer | 1 | Pending |
| 4 | Wire analyzer into pipeline Stage C | Developer | 2 | Pending |
| 5 | Add coverage gate and gap query | Developer | 1 | Pending |
| 6 | Write unit tests | Tech-QA | 2, 3 | Pending |
| 7 | Run lint, type-check, and test suite | Tech-QA | 4, 5, 6 | Pending |

## Notes

- Depends on BEAN-009 (file inventory), BEAN-010 (detector framework), BEAN-019 (surface data model).
- Partial overlap with BEAN-026 (crosscutting concerns) which detects deployment config at a high level. This bean goes deeper — extracting stages, targets, and structured metadata rather than just noting the presence of a Dockerfile.
- CI/CD workflow parsing should extract job names and trigger events, not full step-by-step details.
- Some config files (docker-compose, k8s manifests) are YAML — use safe YAML loading with error tolerance for malformed files.

## Telemetry

| # | Task | Owner | Duration | Tokens In | Tokens Out |
|---|------|-------|----------|-----------|------------|
| 1 | Add BuildDeploySurface to surfaces.py and extend SurfaceCollection | Developer | — | — | — | — |
| 2 | Implement build_deploy.py analyzer | Developer | — | — | — | — |
| 3 | Add bean template renderer for build/deploy | Developer | — | — | — | — |
| 4 | Wire analyzer into pipeline Stage C | Developer | — | — | — | — |
| 5 | Add coverage gate and gap query | Developer | — | — | — | — |
| 6 | Write unit tests | Tech-QA | — | — | — | — |
| 7 | Run lint, type-check, and test suite | Tech-QA | — | — | — | — |

| Metric | Value |
|--------|-------|
| **Total Tasks** | 7 |
| **Total Duration** | — |
| **Total Tokens In** | — |
| **Total Tokens Out** | — |
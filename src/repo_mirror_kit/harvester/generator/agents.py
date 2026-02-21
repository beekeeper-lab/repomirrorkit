"""Agent file generator.

Generates Claude Code agent files (.claude/agents/*.md) tailored to the
analyzed project's characteristics. Always generates developer, architect,
and tech-qa agents; conditionally generates security-engineer and
devops-release agents based on detected surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass

from repo_mirror_kit.harvester.analyzers.surfaces import SurfaceCollection
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.generator.stacks import GeneratedStack


@dataclass(frozen=True)
class GeneratedAgent:
    """A generated agent file.

    Attributes:
        name: Human-readable persona name.
        relative_path: Path relative to the output project folder root.
        content: Markdown content of the agent file.
    """

    name: str
    relative_path: str
    content: str


def generate_agents(
    project_name: str,
    profile: StackProfile,
    surfaces: SurfaceCollection,
    stack_files: list[GeneratedStack],
) -> list[GeneratedAgent]:
    """Generate agent files based on project characteristics.

    Always generates developer, architect, and tech-qa agents. Adds
    security-engineer if auth surfaces exist, and devops-release if
    build/deploy surfaces exist.

    Args:
        project_name: Name of the analyzed project.
        profile: Detected technology stack profile.
        surfaces: All extracted surfaces.
        stack_files: Generated stack convention files (for references).

    Returns:
        List of GeneratedAgent instances ready to write.
    """
    stacks = sorted(profile.stacks.keys())
    stack_refs = [s.relative_path for s in stack_files]

    agents: list[GeneratedAgent] = [
        _generate_developer_agent(project_name, stacks, surfaces, stack_refs),
        _generate_architect_agent(project_name, stacks, surfaces),
        _generate_tech_qa_agent(project_name, stacks, surfaces),
    ]

    if surfaces.auth:
        agents.append(_generate_security_agent(project_name, surfaces))

    if surfaces.build_deploy:
        agents.append(_generate_devops_agent(project_name, surfaces))

    return agents


def _generate_developer_agent(
    project_name: str,
    stacks: list[str],
    surfaces: SurfaceCollection,
    stack_refs: list[str],
) -> GeneratedAgent:
    """Generate the developer agent with project-specific context."""
    stack_line = ", ".join(stacks) if stacks else "unknown"
    stack_ref_lines = (
        "\n".join(f"- `{ref}`" for ref in stack_refs)
        if stack_refs
        else "- No stack conventions generated"
    )

    key_files = _extract_key_files(surfaces, limit=20)
    key_files_lines = (
        "\n".join(f"- `{f}`" for f in key_files)
        if key_files
        else "- No key files identified"
    )

    content = f"""# Developer Agent — {project_name}

## Mission

Implement features, fix bugs, and maintain code quality for {project_name}.

## Project Context

- **Tech stack:** {stack_line}
- **Total surfaces analyzed:** {len(surfaces)}

## Stack Conventions

{stack_ref_lines}

## Key Files

{key_files_lines}

## Operating Principles

1. Follow the stack conventions referenced above.
2. Write tests for all new functionality.
3. Keep changes small and focused — one concern per commit.
4. Use meaningful variable and function names.
5. Handle errors explicitly at system boundaries.
6. Never hardcode secrets or credentials.

## Workflow

1. Read the bean/task specification.
2. Review relevant source files and tests.
3. Implement the change following project conventions.
4. Write or update unit tests.
5. Run linter, type checker, and test suite before marking done.
"""
    return GeneratedAgent(
        name="Developer",
        relative_path=".claude/agents/developer.md",
        content=content,
    )


def _generate_architect_agent(
    project_name: str,
    stacks: list[str],
    surfaces: SurfaceCollection,
) -> GeneratedAgent:
    """Generate the architect agent with system overview."""
    component_count = len(surfaces.components)
    api_count = len(surfaces.apis)
    model_count = len(surfaces.models)
    route_count = len(surfaces.routes)

    content = f"""# Software Architect Agent — {project_name}

## Mission

Design system architecture, review structural decisions, and maintain
architectural integrity for {project_name}.

## System Overview

- **Components:** {component_count}
- **API endpoints:** {api_count}
- **Data models:** {model_count}
- **Routes/pages:** {route_count}
- **Tech stack:** {", ".join(stacks) if stacks else "unknown"}

## Operating Principles

1. Favor simplicity over cleverness.
2. Design for testability and maintainability.
3. Document architectural decisions with rationale.
4. Evaluate trade-offs explicitly before choosing.
5. Keep coupling low and cohesion high.
6. Consider security implications of every design.

## Key Responsibilities

- Review and approve architectural changes.
- Design component boundaries and interfaces.
- Evaluate dependency additions.
- Maintain consistency with established patterns.
"""
    return GeneratedAgent(
        name="Software Architect",
        relative_path=".claude/agents/architect.md",
        content=content,
    )


def _generate_tech_qa_agent(
    project_name: str,
    stacks: list[str],
    surfaces: SurfaceCollection,
) -> GeneratedAgent:
    """Generate the tech-qa agent with test strategy context."""
    test_frameworks = set()
    test_type_counts: dict[str, int] = {}
    for tp in surfaces.test_patterns:
        if tp.framework:
            test_frameworks.add(tp.framework)
        tt = tp.test_type or "unit"
        test_type_counts[tt] = test_type_counts.get(tt, 0) + 1

    fw_line = ", ".join(sorted(test_frameworks)) if test_frameworks else "unknown"
    type_lines = (
        "\n".join(
            f"- {ttype}: {count} test files"
            for ttype, count in sorted(test_type_counts.items())
        )
        if test_type_counts
        else "- No test patterns detected"
    )

    content = f"""# Tech-QA / Test Engineer Agent — {project_name}

## Mission

Ensure code quality, test coverage, and adherence to project standards
for {project_name}.

## Test Strategy

- **Test frameworks:** {fw_line}
- **Total test pattern surfaces:** {len(surfaces.test_patterns)}

### Test Distribution

{type_lines}

## Operating Principles

1. Every feature needs tests before it ships.
2. Test behavior, not implementation details.
3. Maintain coverage gates — no regressions.
4. Run the full quality suite: lint, type-check, test.
5. Flag flaky tests immediately.
6. Prefer fast, isolated unit tests; use integration tests sparingly.

## Quality Gates

- Linter passes with zero warnings.
- Type checker passes in strict mode.
- All existing tests pass.
- New code has test coverage.
"""
    return GeneratedAgent(
        name="Tech-QA / Test Engineer",
        relative_path=".claude/agents/tech-qa.md",
        content=content,
    )


def _generate_security_agent(
    project_name: str,
    surfaces: SurfaceCollection,
) -> GeneratedAgent:
    """Generate the security agent when auth surfaces are detected."""
    auth_names = [a.name for a in surfaces.auth[:10]]
    auth_lines = (
        "\n".join(f"- {name}" for name in auth_names)
        if auth_names
        else "- No specific auth surfaces"
    )

    content = f"""# Security Engineer Agent — {project_name}

## Mission

Review security implications, enforce auth patterns, and assess
vulnerability exposure for {project_name}.

## Auth Surfaces Detected

{auth_lines}

## Operating Principles

1. Every endpoint must be authenticated unless explicitly documented as public.
2. Validate and sanitize all external inputs.
3. Use parameterized queries — never string concatenation for queries.
4. Audit logging for security-relevant events.
5. Apply least privilege to all service accounts and roles.
6. Review dependency updates for known vulnerabilities.

## Key Responsibilities

- Review auth and authorization implementations.
- Flag sensitive data handling (PII, credentials).
- Assess API security posture.
- Review access control on new endpoints.
"""
    return GeneratedAgent(
        name="Security Engineer",
        relative_path=".claude/agents/security-engineer.md",
        content=content,
    )


def _generate_devops_agent(
    project_name: str,
    surfaces: SurfaceCollection,
) -> GeneratedAgent:
    """Generate the devops agent when build/deploy surfaces are detected."""
    build_tools = set()
    for bd in surfaces.build_deploy:
        if bd.tool:
            build_tools.add(bd.tool)

    tools_line = ", ".join(sorted(build_tools)) if build_tools else "unknown"

    content = f"""# DevOps / Release Engineer Agent — {project_name}

## Mission

Manage build pipelines, deployment configurations, and release processes
for {project_name}.

## Build/Deploy Tools Detected

- **Tools:** {tools_line}
- **Total build/deploy surfaces:** {len(surfaces.build_deploy)}

## Operating Principles

1. Builds must be reproducible and deterministic.
2. CI/CD pipelines should fail fast on errors.
3. Never store secrets in CI/CD configuration — use secret managers.
4. Container images should be minimal and security-scanned.
5. Infrastructure changes go through code review.
6. Maintain rollback capability for all deployments.

## Key Responsibilities

- Maintain CI/CD pipeline configurations.
- Review Dockerfile and container changes.
- Manage environment configurations.
- Coordinate release processes.
"""
    return GeneratedAgent(
        name="DevOps / Release Engineer",
        relative_path=".claude/agents/devops-release.md",
        content=content,
    )


def _extract_key_files(
    surfaces: SurfaceCollection,
    limit: int = 20,
) -> list[str]:
    """Extract key file paths from surfaces for developer context."""
    files: set[str] = set()
    for surface in surfaces:
        for ref in surface.source_refs:
            files.add(ref.file_path)
            if len(files) >= limit:
                return sorted(files)
    return sorted(files)

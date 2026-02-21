"""Project folder assembler.

Orchestrates CLAUDE.md generation, agent file generation, and stack
convention file generation, writing all output to the correct directory
structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import SurfaceCollection
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.generator.agents import GeneratedAgent, generate_agents
from repo_mirror_kit.harvester.generator.claude_md import generate_claude_md
from repo_mirror_kit.harvester.generator.stacks import generate_stacks

logger = structlog.get_logger()


@dataclass(frozen=True)
class GeneratorResult:
    """Result of the project folder generation.

    Attributes:
        output_dir: Root path of the generated project folder.
        generated_files: List of paths to all generated files.
        agent_count: Number of agent files generated.
        stack_count: Number of stack convention files generated.
    """

    output_dir: Path
    generated_files: list[Path]
    agent_count: int
    stack_count: int


def assemble_project_folder(
    output_dir: Path,
    project_name: str,
    surfaces: SurfaceCollection,
    profile: StackProfile,
) -> GeneratorResult:
    """Assemble a complete Claude Code project folder.

    Orchestrates generation of CLAUDE.md, agent files, and stack
    convention files, writing them to the output directory.

    Args:
        output_dir: Root output directory for the harvest run.
        project_name: Name of the analyzed project.
        surfaces: All extracted surfaces.
        profile: Detected technology stack profile.

    Returns:
        A GeneratorResult summarizing what was generated.
    """
    project_dir = output_dir / "project-folder"
    generated_files: list[Path] = []

    logger.info(
        "generator_starting",
        project_name=project_name,
        output_dir=str(project_dir),
    )

    # Step 1: Generate stack convention files
    stack_files = generate_stacks(profile, surfaces)
    for sf in stack_files:
        path = project_dir / sf.relative_path
        _write_file(path, sf.content)
        generated_files.append(path)

    logger.info("generator_stacks_done", count=len(stack_files))

    # Step 2: Generate agent files
    agents = generate_agents(project_name, profile, surfaces, stack_files)
    for agent in agents:
        path = project_dir / agent.relative_path
        _write_file(path, agent.content)
        generated_files.append(path)

    logger.info("generator_agents_done", count=len(agents))

    # Step 3: Generate CLAUDE.md (needs agent and stack info)
    agent_metadata = _build_agent_metadata(agents)
    stack_rel_paths = [sf.relative_path for sf in stack_files]

    claude_md_content = generate_claude_md(
        project_name=project_name,
        surfaces=surfaces,
        profile=profile,
        agents=agent_metadata,
        stack_files=stack_rel_paths,
    )
    claude_md_path = project_dir / "CLAUDE.md"
    _write_file(claude_md_path, claude_md_content)
    generated_files.append(claude_md_path)

    logger.info("generator_claude_md_done")

    result = GeneratorResult(
        output_dir=project_dir,
        generated_files=generated_files,
        agent_count=len(agents),
        stack_count=len(stack_files),
    )

    logger.info(
        "generator_complete",
        total_files=len(generated_files),
        agent_count=result.agent_count,
        stack_count=result.stack_count,
    )

    return result


def _write_file(path: Path, content: str) -> None:
    """Write content to a file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_agent_metadata(agents: list[GeneratedAgent]) -> list[dict[str, str]]:
    """Build agent metadata dicts for CLAUDE.md team roster."""
    return [{"name": agent.name, "file": agent.relative_path} for agent in agents]

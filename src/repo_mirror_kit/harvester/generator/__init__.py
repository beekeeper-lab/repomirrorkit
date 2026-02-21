"""Claude Code project folder generator.

Synthesizes harvest artifacts (surfaces, stack profile, beans) into a
ready-to-use Claude Code project folder: CLAUDE.md, agent files, and
stack convention files.
"""

from __future__ import annotations

from repo_mirror_kit.harvester.generator.assembler import (
    GeneratorResult,
    assemble_project_folder,
)

__all__ = ["GeneratorResult", "assemble_project_folder"]

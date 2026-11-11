"""Stage H: post-run source cleanup (BEAN-080).

Mirror-mode output must be a self-contained requirements package: after a
fully successful run, the cloned working copy (``<out>/repo/``, including
its ``.git/``) is removed so the package contains no original source and
no Git history. Deletion is guarded by hard safety invariants — this
module must never remove anything the harvester did not create.

See ``SPEC-MIRROR-MODE.md`` Phase 1 (M1.3) for the design.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.state import StateManager

logger = structlog.get_logger()


class CleanupError(Exception):
    """Raised when a Stage H safety invariant is violated."""


@dataclass(frozen=True)
class CleanupResult:
    """Outcome of the Stage H source cleanup.

    Attributes:
        removed: Whether the working copy was removed.
        files_removed: Number of files deleted (including ``.git`` contents).
        bytes_freed: Total on-disk bytes deleted.
        stray_git_removed: Stray ``.git`` entries removed elsewhere under
            the output directory (e.g. submodule gitlink files copied into
            ``project-folder/``).
    """

    removed: bool
    files_removed: int
    bytes_freed: int
    stray_git_removed: list[str]


def remove_source(output_dir: Path, state: StateManager) -> CleanupResult:
    """Remove ``<output_dir>/repo`` (including ``.git``) after a successful run.

    Safety invariants, all mandatory and checked in order:

    1. The target is exactly ``output_dir / "repo"``, is not a symlink, and
       resolves to a directory strictly inside ``output_dir``.
    2. ``state.json`` records a completed Stage A clone — the harvester
       never deletes a ``repo/`` it did not create.
    3. The target contains a ``.git`` entry (sanity check that it is a
       clone). If state confirms the clone but ``.git`` is absent, cleanup
       proceeds with a warning.
    4. After deletion, any stray ``.git`` entries remaining under
       ``output_dir`` (e.g. submodule gitlink files that ``copytree``
       carried into ``project-folder/``) are removed; failure to remove
       one is an error, never silence.

    Args:
        output_dir: The harvest output root.
        state: State manager whose loaded state must record Stage A done.

    Returns:
        A CleanupResult describing what was removed.

    Raises:
        CleanupError: If any safety invariant is violated.
    """
    repo_dir = output_dir / "repo"

    # Invariant 1: exact target, no symlink, resolves inside output_dir.
    if repo_dir.is_symlink():
        raise CleanupError(
            f"Refusing cleanup: {repo_dir} is a symlink, not the cloned working copy."
        )
    if not repo_dir.is_dir():
        raise CleanupError(
            f"Refusing cleanup: {repo_dir} does not exist or is not a directory."
        )
    resolved = repo_dir.resolve()
    output_resolved = output_dir.resolve()
    try:
        relative = resolved.relative_to(output_resolved)
    except ValueError as err:
        raise CleanupError(
            f"Refusing cleanup: {repo_dir} resolves outside the output "
            f"directory ({resolved})."
        ) from err
    if str(relative) != "repo":
        raise CleanupError(
            f"Refusing cleanup: {repo_dir} does not resolve to "
            f"<output_dir>/repo (got {resolved})."
        )

    # Invariant 2: only delete a working copy the harvester cloned.
    if not state.is_stage_done("A"):
        raise CleanupError(
            "Refusing cleanup: state.json does not record a completed "
            "clone (Stage A) for this output directory."
        )

    # Invariant 3: sanity-check the target looks like a clone.
    if not (repo_dir / ".git").exists():
        logger.warning(
            "cleanup_no_git_dir",
            repo_dir=str(repo_dir),
            msg="No .git entry in the working copy; proceeding because "
            "state.json confirms Stage A cloned it.",
        )

    files_removed, bytes_freed = _measure(repo_dir)
    shutil.rmtree(repo_dir)

    # Invariant 4: no .git may remain anywhere under the output directory.
    stray_removed = _remove_stray_git_entries(output_dir)

    logger.info(
        "cleanup_complete",
        repo_dir=str(repo_dir),
        files_removed=files_removed,
        bytes_freed=bytes_freed,
        stray_git_removed=stray_removed,
    )
    return CleanupResult(
        removed=True,
        files_removed=files_removed,
        bytes_freed=bytes_freed,
        stray_git_removed=stray_removed,
    )


def _measure(root: Path) -> tuple[int, int]:
    """Count files and total bytes under *root* (``.git`` included).

    Symlinks are counted but not followed.
    """
    files = 0
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            fp = Path(dirpath) / name
            files += 1
            if fp.is_symlink():
                continue
            try:
                total += fp.stat().st_size
            except OSError:
                continue
    return files, total


def _remove_stray_git_entries(output_dir: Path) -> list[str]:
    """Remove any remaining ``.git`` files/directories under *output_dir*.

    Generated artifacts can legitimately carry gitlink files — e.g.
    ``project-folder/.claude/shared/.git`` copied from a submodule checkout
    by the Stage G assembler. Those are inert but violate the mirror
    guarantee ("no .git anywhere"), so they are removed with a warning.

    Returns:
        Output-relative paths of the removed entries.

    Raises:
        CleanupError: If a ``.git`` entry is found but cannot be removed.
    """
    removed: list[str] = []
    for stray in sorted(output_dir.rglob(".git")):
        relative = str(stray.relative_to(output_dir))
        logger.warning("cleanup_stray_git_entry", path=relative)
        try:
            if stray.is_dir() and not stray.is_symlink():
                shutil.rmtree(stray)
            else:
                stray.unlink()
        except OSError as err:
            raise CleanupError(
                f"A .git entry remains after cleanup and could not be "
                f"removed: {relative} ({err})"
            ) from err
        removed.append(relative)
    return removed

"""Git operations for harvester repository analysis.

Provides clone, ref checkout, line ending normalization, and symlink
safety checks for Stage A of the harvester pipeline.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger()

# scp-like git URL form, e.g. ``git@github.com:user/repo.git``.
_SCP_LIKE_URL_RE = re.compile(r"^[\w.-]+@[\w.-]+:[\w./~-]+$")

# Supported URL prefixes for ``git clone``. Anything not starting with one of
# these (or an absolute path, or matching the scp-like form above) is rejected
# by ``_validate_clone_url`` to prevent argv-flag confusion and unsupported
# transport vectors.
_VALID_URL_PREFIXES: tuple[str, ...] = (
    "https://",
    "http://",
    "ssh://",
    "file://",
)


class GitNotFoundError(Exception):
    """Raised when git is not available on PATH."""


class GitCloneError(Exception):
    """Raised when a git clone operation fails."""


class GitRefError(Exception):
    """Raised when a git ref checkout fails."""


def validate_clone_url(url: str) -> None:
    """Validate that *url* is one of the supported clone source forms.

    The single canonical URL validator for the harvester. Used by:

    - ``clone_repository`` (defense-in-depth before the subprocess call)
    - ``HarvestConfig.__post_init__`` (boundary validation at config build)
    - ``services.clone_service.validate_git_url`` (GUI-friendly wrapper that
      converts the raised exception to a user-facing message string)

    Rejects empty/whitespace strings, URLs starting with ``-`` (could be
    misparsed by ``git clone`` as a flag), URLs containing whitespace, and
    anything outside the documented allow-list (``https://``, ``http://``,
    ``ssh://``, ``file://``, scp-like ``user@host:path``, or absolute local
    paths beginning with ``/``).

    Raises:
        GitCloneError: If *url* fails validation.
    """
    if not url or not url.strip():
        raise GitCloneError("Repository URL cannot be empty")
    if url != url.strip():
        raise GitCloneError(
            f"Repository URL cannot have leading or trailing whitespace: {url!r}"
        )
    if " " in url:
        raise GitCloneError(f"Repository URL cannot contain spaces: {url!r}")
    if url.startswith("-"):
        raise GitCloneError(
            f"Repository URL cannot start with '-' (could be parsed as a "
            f"git flag): {url!r}"
        )
    if url.startswith(_VALID_URL_PREFIXES):
        return
    if _SCP_LIKE_URL_RE.match(url):
        return
    if url.startswith("/"):
        return
    raise GitCloneError(
        "Repository URL does not match a supported scheme "
        "(https://, http://, ssh://, file://, "
        "scp-like user@host:path, or absolute local path): "
        f"{url!r}"
    )


@dataclass
class CloneResult:
    """Result of a clone and normalize operation.

    Args:
        repo_dir: Path to the cloned repository.
        skipped_symlinks: Symlinks that pointed outside the repo.
        normalized_files: Number of files with line endings normalized.
    """

    repo_dir: Path
    skipped_symlinks: list[str]
    normalized_files: int


def check_git_available() -> None:
    """Verify that git is available on the system PATH.

    Raises:
        GitNotFoundError: If git is not found on PATH.
    """
    if shutil.which("git") is None:
        msg = (
            "git is not installed or not on PATH. "
            "Install git and ensure it is accessible."
        )
        raise GitNotFoundError(msg)


def _compute_total_size(workdir: Path) -> int:
    """Sum the on-disk size of regular files under *workdir* (excluding ``.git``).

    Symlinks are not followed. Returns the total in bytes.
    """
    total = 0
    for dirpath, dirnames, filenames in os.walk(workdir):
        # Skip the .git directory entirely.
        if ".git" in Path(dirpath).parts:
            dirnames.clear()
            continue
        for name in filenames:
            fp = Path(dirpath) / name
            if fp.is_symlink():
                continue
            try:
                total += fp.stat().st_size
            except OSError:
                continue
    return total


def clone_repository(
    url: str,
    ref: str | None,
    workdir: Path,
    *,
    max_total_bytes: int | None = None,
) -> CloneResult:
    """Clone a repository, checkout a ref, and normalize the working copy.

    Clones the repository at *url* into *workdir*, optionally checks out
    *ref*, normalizes line endings to LF, and identifies symlinks that
    point outside the repository boundary.

    Args:
        url: The git repository URL to clone.
        ref: Branch, tag, or SHA to checkout. None for default branch.
        workdir: Directory to clone into (must not already exist).

    Returns:
        A CloneResult with the repo path, skipped symlinks, and
        normalized file count.

    Raises:
        GitNotFoundError: If git is not on PATH.
        GitCloneError: If the clone operation fails.
        GitRefError: If the specified ref cannot be checked out.
    """
    check_git_available()
    validate_clone_url(url)

    logger.info("clone_starting", url=url, ref=ref, workdir=str(workdir))

    _run_clone(url, workdir)

    if max_total_bytes is not None:
        actual = _compute_total_size(workdir)
        if actual > max_total_bytes:
            # Clean up the partial clone so we never leave a half-state on disk.
            shutil.rmtree(workdir, ignore_errors=True)
            raise GitCloneError(
                f"Cloned repository size {actual} bytes exceeds cap "
                f"of {max_total_bytes} bytes. Increase --max-total-bytes "
                f"or use --include/--exclude to narrow scope."
            )
        logger.info(
            "clone_size_ok",
            actual_bytes=actual,
            cap_bytes=max_total_bytes,
        )

    if ref is not None:
        _checkout_ref(ref, workdir)

    skipped = _check_symlinks(workdir)
    normalized = _normalize_line_endings(workdir)

    logger.info(
        "clone_complete",
        repo_dir=str(workdir),
        skipped_symlinks=len(skipped),
        normalized_files=normalized,
    )

    return CloneResult(
        repo_dir=workdir,
        skipped_symlinks=skipped,
        normalized_files=normalized,
    )


def _run_clone(url: str, workdir: Path) -> None:
    """Execute git clone into workdir.

    Args:
        url: The repository URL.
        workdir: Target directory for the clone.

    Raises:
        GitCloneError: If the clone process fails.
    """
    # ``--`` ensures that a URL beginning with ``-`` cannot be reinterpreted by
    # git as a flag (defense-in-depth alongside ``_validate_clone_url``).
    cmd = ["git", "clone", "--progress", "--", url, str(workdir)]
    logger.info("clone_running", cmd=cmd)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        msg = (
            "git is not installed or not on PATH. "
            "Install git and ensure it is accessible."
        )
        raise GitNotFoundError(msg) from exc

    if result.returncode != 0:
        stderr = result.stderr.strip()
        msg = f"git clone failed (exit code {result.returncode}): {stderr}"
        raise GitCloneError(msg)

    logger.info("clone_succeeded", workdir=str(workdir))


def _checkout_ref(ref: str, workdir: Path) -> None:
    """Checkout a specific ref in the cloned repository.

    Args:
        ref: Branch, tag, or SHA to checkout.
        workdir: Path to the cloned repository.

    Raises:
        GitRefError: If the ref cannot be checked out.
    """
    cmd = ["git", "checkout", ref]
    logger.info("ref_checkout", ref=ref, workdir=str(workdir))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(workdir),
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        msg = f"Failed to checkout ref '{ref}': {stderr}"
        raise GitRefError(msg)

    logger.info("ref_checkout_complete", ref=ref)


def _check_symlinks(workdir: Path) -> list[str]:
    """Identify symlinks that point outside the repository boundary.

    Walks the working directory and checks each symlink. Symlinks whose
    resolved target is outside the repository root are logged and
    collected for skipping.

    Args:
        workdir: Root of the cloned repository.

    Returns:
        List of relative path strings for symlinks pointing outside repo.
    """
    repo_root = workdir.resolve()
    skipped: list[str] = []

    for dirpath, _dirnames, filenames in os.walk(workdir):
        current = Path(dirpath)

        # Skip .git directory
        if ".git" in current.parts:
            continue

        for name in filenames:
            filepath = current / name
            if filepath.is_symlink():
                target = filepath.resolve()
                try:
                    target.relative_to(repo_root)
                except ValueError:
                    relative = str(filepath.relative_to(workdir))
                    logger.warning(
                        "symlink_outside_repo",
                        symlink=relative,
                        target=str(target),
                    )
                    skipped.append(relative)

        # Also check directory symlinks
        for name in _dirnames:
            dirpath_entry = current / name
            if dirpath_entry.is_symlink():
                target = dirpath_entry.resolve()
                try:
                    target.relative_to(repo_root)
                except ValueError:
                    relative = str(dirpath_entry.relative_to(workdir))
                    logger.warning(
                        "symlink_outside_repo",
                        symlink=relative,
                        target=str(target),
                    )
                    skipped.append(relative)

    if skipped:
        logger.info("symlinks_skipped", count=len(skipped), paths=skipped)

    return skipped


def _normalize_line_endings(workdir: Path) -> int:
    """Normalize CRLF line endings to LF in text files.

    Walks the working directory and converts any CRLF sequences to LF
    in files that appear to be text. Binary files are skipped.

    Args:
        workdir: Root of the cloned repository.

    Returns:
        Number of files that had line endings normalized.
    """
    normalized_count = 0

    for dirpath, _dirnames, filenames in os.walk(workdir):
        current = Path(dirpath)

        # Skip .git directory
        if ".git" in current.parts:
            continue

        for name in filenames:
            filepath = current / name

            # Skip symlinks
            if filepath.is_symlink():
                continue

            if _normalize_file(filepath):
                normalized_count += 1

    if normalized_count > 0:
        logger.info("line_endings_normalized", count=normalized_count)

    return normalized_count


def _normalize_file(filepath: Path) -> bool:
    """Normalize a single file's line endings from CRLF to LF.

    Args:
        filepath: Path to the file to normalize.

    Returns:
        True if the file was modified, False otherwise.
    """
    try:
        content = filepath.read_bytes()
    except OSError:
        return False

    if b"\x00" in content:
        # Binary file, skip
        return False

    if b"\r\n" not in content:
        return False

    normalized = content.replace(b"\r\n", b"\n")
    filepath.write_bytes(normalized)
    return True

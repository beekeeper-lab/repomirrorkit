"""Read-only, sandboxed repository tools for the enrichment agent (BEAN-068).

The agent may look anywhere inside the cloned repo — but only look. Threat
model: the repo is untrusted, and so are the tool *results* (they are repo
content flowing back into the model). Mitigations:

- paths are resolved and must stay inside the clone (``..``, absolute paths and
  symlink escapes are refused);
- ``.git``, ``.env*`` (except ``.env.example``), private keys and credential
  files are never readable;
- every result is size-capped and wrapped in a ``<repo_file>`` /
  ``<repo_search>`` / ``<repo_listing>`` envelope with the same closing-tag
  escaping used for prompts, and the system prompt declares envelopes data;
- ``grep`` bounds pattern length, per-line length, match count, file count and
  wall-clock time (regex DoS guard);
- there are no write tools of any kind.
"""

from __future__ import annotations

import fnmatch
import re
import time
from pathlib import Path
from typing import Any

from repo_mirror_kit.harvester.llm.prompts import _escape_repo_payload

MAX_READ_BYTES = 24_000
MAX_GREP_MATCHES = 40
MAX_GREP_FILES = 4_000
MAX_GREP_SECONDS = 3.0
MAX_LINE_CHARS = 400
MAX_LIST_ENTRIES = 200
MAX_PATTERN_CHARS = 200

_SKIP_DIRS = frozenset(
    {".git", "node_modules", "dist", "build", ".next", "__pycache__", ".venv", "venv"}
)
_DENY_NAME_GLOBS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa*",
    "id_ed25519*",
    "credentials*",
    "*.keystore",
)
_ALLOW_NAMES = frozenset({".env.example", ".env.sample", ".env.template"})

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "read_file",
        "description": (
            "Read a text file from the repository (read-only). Use start_line/"
            "end_line to page through large files."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Repo-relative path."},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
            },
            "required": ["path"],
        },
    },
    {
        "name": "grep",
        "description": (
            "Search repository files with a regular expression. Returns "
            "path:line: text for up to 40 matches."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "glob": {
                    "type": "string",
                    "description": "Optional filename glob, e.g. '*.py'.",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "list_dir",
        "description": "List entries of a repository directory (read-only).",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "default": "."}},
        },
    },
]


def _envelope(tag: str, attrs: str, body: str) -> str:
    return f"<repo_{tag} {attrs}>\n{_escape_repo_payload(body)}\n</repo_{tag}>"


class RepoTools:
    """Executes the agent's tool calls against a cloned repository."""

    def __init__(self, workdir: Path) -> None:
        self._root = workdir.resolve()
        self.calls = 0

    # -- sandbox -----------------------------------------------------------
    def _resolve(self, rel: str) -> Path | None:
        if not isinstance(rel, str) or "\x00" in rel:
            return None
        candidate = (self._root / rel).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError:
            return None
        parts = candidate.relative_to(self._root).parts
        if any(p == ".git" for p in parts):
            return None
        return candidate

    @staticmethod
    def _denied(path: Path) -> bool:
        name = path.name
        if name in _ALLOW_NAMES:
            return False
        return any(fnmatch.fnmatch(name, g) for g in _DENY_NAME_GLOBS)

    # -- dispatch ----------------------------------------------------------
    def execute(self, name: str, args: dict[str, Any]) -> str:
        """Run a tool; never raises — errors come back as text."""
        self.calls += 1
        try:
            if name == "read_file":
                return self._read_file(args)
            if name == "grep":
                return self._grep(args)
            if name == "list_dir":
                return self._list_dir(args)
        except Exception as exc:
            return f"error: {type(exc).__name__}: {exc}"
        return f"error: unknown tool {name!r}"

    # -- tools -------------------------------------------------------------
    def _read_file(self, args: dict[str, Any]) -> str:
        rel = str(args.get("path", ""))
        path = self._resolve(rel)
        if path is None or self._denied(path):
            return "error: path not allowed"
        if not path.is_file():
            return "error: file not found"
        data = path.read_bytes()
        if b"\x00" in data[:2048]:
            return "error: binary file"
        text = data.decode("utf-8", errors="replace")
        lines = text.splitlines()
        start = max(1, int(args.get("start_line") or 1))
        end = int(args.get("end_line") or len(lines))
        chunk = "\n".join(
            f"{n}: {line[:MAX_LINE_CHARS]}"
            for n, line in enumerate(lines[start - 1 : end], start=start)
        )
        truncated = ""
        if len(chunk) > MAX_READ_BYTES:
            chunk = chunk[:MAX_READ_BYTES]
            truncated = "\n... (truncated; request a narrower line range)"
        return _envelope("file", f'path="{rel}"', chunk + truncated)

    def _iter_files(self, glob: str | None) -> list[Path]:
        files: list[Path] = []
        for path in sorted(self._root.rglob("*")):
            if len(files) >= MAX_GREP_FILES:
                break
            if not path.is_file() or path.is_symlink():
                continue
            rel_parts = path.relative_to(self._root).parts
            if any(p in _SKIP_DIRS for p in rel_parts):
                continue
            if self._denied(path):
                continue
            if glob and not fnmatch.fnmatch(path.name, glob):
                continue
            files.append(path)
        return files

    def _grep(self, args: dict[str, Any]) -> str:
        pattern = str(args.get("pattern", ""))
        if not pattern or len(pattern) > MAX_PATTERN_CHARS:
            return "error: pattern missing or too long"
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            return f"error: invalid regex: {exc}"
        glob = args.get("glob")
        deadline = time.monotonic() + MAX_GREP_SECONDS
        matches: list[str] = []
        for path in self._iter_files(str(glob) if glob else None):
            if time.monotonic() > deadline or len(matches) >= MAX_GREP_MATCHES:
                break
            try:
                if path.stat().st_size > 400_000:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for n, line in enumerate(text.splitlines(), start=1):
                if regex.search(line[:MAX_LINE_CHARS]):
                    rel = path.relative_to(self._root).as_posix()
                    matches.append(f"{rel}:{n}: {line[:MAX_LINE_CHARS].strip()}")
                    if len(matches) >= MAX_GREP_MATCHES:
                        break
        body = "\n".join(matches) if matches else "(no matches)"
        return _envelope("search", f'pattern="{_escape_repo_payload(pattern)}"', body)

    def _list_dir(self, args: dict[str, Any]) -> str:
        rel = str(args.get("path") or ".")
        path = self._resolve(rel)
        if path is None or not path.is_dir():
            return "error: directory not allowed or not found"
        entries: list[str] = []
        for child in sorted(path.iterdir()):
            if child.name == ".git" or self._denied(child):
                continue
            entries.append(child.name + ("/" if child.is_dir() else ""))
            if len(entries) >= MAX_LIST_ENTRIES:
                entries.append("... (truncated)")
                break
        return _envelope("listing", f'path="{rel}"', "\n".join(entries) or "(empty)")

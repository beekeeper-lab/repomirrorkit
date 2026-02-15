#!/usr/bin/env python3
"""PostToolUse hook: auto-stamp telemetry timestamps in bean/task files.

Fires after Edit/Write on files matching:
  ai/beans/BEAN-*/bean.md
  ai/beans/BEAN-*/tasks/*.md

Stamps Started/Completed timestamps and computes Duration when status
transitions are detected. Only overwrites fields whose value is the
sentinel em-dash (—).

When a bean is marked Done, duration is computed from git timestamps
(first commit on the feature branch → now) for second-level precision.
Falls back to Started/Completed metadata if git is unavailable.

Reads hook input JSON from stdin, writes JSON message to stdout when
a file is modified.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

SENTINEL = "—"
TIMESTAMP_FMT = "%Y-%m-%d %H:%M"

# Patterns to match bean and task files (relative paths from repo root)
BEAN_RE = re.compile(r"ai/beans/BEAN-\d+-[^/]+/bean\.md$")
TASK_RE = re.compile(r"ai/beans/BEAN-\d+-[^/]+/tasks/.*\.md$")


def now_stamp() -> str:
    """Return current timestamp in YYYY-MM-DD HH:MM format."""
    return datetime.now().strftime(TIMESTAMP_FMT)


def parse_metadata_field(content: str, field: str) -> str | None:
    """Extract value of a bold field from a markdown metadata table.

    Looks for rows like: | **Field** | Value |
    Returns the stripped value, or None if not found.
    """
    pattern = re.compile(
        r"^\|\s*\*\*" + re.escape(field) + r"\*\*\s*\|\s*(.*?)\s*\|",
        re.MULTILINE,
    )
    m = pattern.search(content)
    if m:
        return m.group(1).strip()
    return None


def replace_metadata_field(content: str, field: str, value: str) -> str:
    """Replace value of a bold field in a markdown metadata table.

    Replaces: | **Field** | old_value |
    With:     | **Field** | new_value |
    """
    pattern = re.compile(
        r"(^\|\s*\*\*" + re.escape(field) + r"\*\*\s*\|\s*)(.*?)(\s*\|)",
        re.MULTILINE,
    )
    return pattern.sub(rf"\g<1>{value}\3", content, count=1)


def format_seconds(seconds: float) -> str:
    """Format a duration in seconds to human-readable string.

    Returns '< 1m' for <60s, 'Xm' for <1h, 'Xh Ym' for >=1h.
    """
    total_minutes = max(0, int(seconds // 60))
    if total_minutes == 0:
        return "< 1m"
    if total_minutes < 60:
        return f"{total_minutes}m"
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if minutes == 0:
        return f"{hours}h"
    return f"{hours}h {minutes}m"


def format_duration(started: str, completed: str) -> str:
    """Compute human-readable duration between two timestamps.

    Returns 'Xm' for <1h, 'Xh Ym' for >=1h. Returns '< 1m' on parse error.
    """
    try:
        dt_start = datetime.strptime(started.strip(), TIMESTAMP_FMT)
        dt_end = datetime.strptime(completed.strip(), TIMESTAMP_FMT)
        delta = dt_end - dt_start
        return format_seconds(max(0, delta.total_seconds()))
    except (ValueError, TypeError):
        return "< 1m"


def git_branch_duration() -> str | None:
    """Compute duration from the first commit on the current feature branch.

    Uses git to find the first commit on the current branch that isn't on
    'test' or 'main', and computes elapsed time from that commit to now.
    Returns a formatted duration string, or None if git data is unavailable.
    """
    try:
        # Get current branch name
        branch = subprocess.run(
            ["git", "branch", "--show-current"],  # noqa: S607 — hardcoded git path
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()

        if not branch or branch in ("main", "test"):
            return None

        # Find the merge base with test (or main as fallback)
        for base in ("test", "main"):
            result = subprocess.run(  # noqa: S603 — hardcoded git command
                ["git", "merge-base", base, "HEAD"],  # noqa: S607 — hardcoded git path
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                merge_base = result.stdout.strip()
                break
        else:
            return None

        # Get timestamp of first commit after merge base
        result = subprocess.run(  # noqa: S603 — hardcoded git command
            ["git", "log", "--format=%aI", "--reverse", f"{merge_base}..HEAD"],  # noqa: S607 — hardcoded git path
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None

        first_commit_ts = result.stdout.strip().split("\n")[0]
        dt_start = datetime.fromisoformat(first_commit_ts)
        dt_now = datetime.now(UTC)
        # Ensure both are offset-aware for comparison
        if dt_start.tzinfo is None:
            dt_start = dt_start.replace(tzinfo=UTC)
        delta = (dt_now - dt_start).total_seconds()
        return format_seconds(max(0, delta))

    except Exception:
        return None


def count_done_tasks(content: str) -> int:
    """Count rows with 'Done' status in the Tasks table of a bean.md.

    Looks for the table under ## Tasks with columns: # | Task | Owner | Depends On | Status
    Counts rows where the Status column is 'Done'.
    """
    count = 0
    in_tasks = False
    header_seen = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Tasks"):
            in_tasks = True
            continue
        if in_tasks and stripped.startswith("##"):
            break
        if not in_tasks:
            continue
        if not stripped.startswith("|"):
            if header_seen and stripped and not stripped.startswith(">"):
                break
            continue
        # Skip separator rows
        if re.match(r"^\|[\s\-|]+\|$", stripped):
            header_seen = True
            continue
        # Skip header row (contains "Task" or "#")
        if not header_seen:
            header_seen = False
            continue

        cells = [c.strip() for c in stripped.split("|")]
        # cells[0] is empty (before first |), last is empty (after last |)
        cells = [c for c in cells if c]
        if len(cells) >= 5 and cells[-1].lower() == "done":
            count += 1

    return count


def count_total_tasks(content: str) -> int:
    """Count total task rows in the Tasks table of a bean.md."""
    count = 0
    in_tasks = False
    separator_seen = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Tasks"):
            in_tasks = True
            continue
        if in_tasks and stripped.startswith("##"):
            break
        if not in_tasks:
            continue
        if not stripped.startswith("|"):
            if separator_seen and stripped and not stripped.startswith(">"):
                break
            continue
        if re.match(r"^\|[\s\-|]+\|$", stripped):
            separator_seen = True
            continue
        if not separator_seen:
            continue
        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c]
        if len(cells) >= 2:
            count += 1

    return count


def handle_bean_file(path: Path, now: str) -> list[str]:
    """Process a bean.md file for telemetry stamping.

    Returns list of actions taken (empty if no changes).
    """
    content = path.read_text(encoding="utf-8")
    original = content
    actions = []

    status = parse_metadata_field(content, "Status")
    started = parse_metadata_field(content, "Started")
    completed = parse_metadata_field(content, "Completed")

    # Status = "In Progress" + Started = sentinel → stamp Started
    if status and status.lower() == "in progress" and started == SENTINEL:
        content = replace_metadata_field(content, "Started", now)
        actions.append("Started")

    # Status = "Done" + Completed = sentinel → stamp Completed + Duration
    if status and status.lower() == "done" and completed == SENTINEL:
        # If Started is also sentinel, stamp it too
        cur_started = parse_metadata_field(content, "Started")
        if cur_started == SENTINEL:
            content = replace_metadata_field(content, "Started", now)
            cur_started = now
            actions.append("Started")

        content = replace_metadata_field(content, "Completed", now)
        actions.append("Completed")

        cur_duration = parse_metadata_field(content, "Duration")
        if cur_duration == SENTINEL:
            # Prefer git-based duration (second-level precision) over
            # Started→Completed metadata (minute-level, often 0m for fast beans)
            duration = git_branch_duration() or format_duration(cur_started, now)
            content = replace_metadata_field(content, "Duration", duration)
            actions.append(f"Duration={duration}")

    # Status = "Done" → fill Total Tasks in Telemetry summary
    if status and status.lower() == "done":
        total_tasks_val = parse_metadata_field(content, "Total Tasks")
        if total_tasks_val == SENTINEL:
            total = count_total_tasks(content)
            content = replace_metadata_field(
                content, "Total Tasks", str(total)
            )
            actions.append(f"Total Tasks={total}")

        total_dur_val = parse_metadata_field(content, "Total Duration")
        if total_dur_val == SENTINEL:
            # Prefer git-based duration; fall back to Started/Completed
            total_dur = git_branch_duration()
            if not total_dur:
                final_started = parse_metadata_field(content, "Started")
                final_completed = parse_metadata_field(content, "Completed")
                if (
                    final_started and final_started != SENTINEL
                    and final_completed and final_completed != SENTINEL
                ):
                    total_dur = format_duration(final_started, final_completed)
            if total_dur:
                content = replace_metadata_field(
                    content, "Total Duration", total_dur
                )
                actions.append(f"Total Duration={total_dur}")

    if content != original:
        path.write_text(content, encoding="utf-8")

    return actions


def handle_task_file(path: Path, now: str) -> list[str]:
    """Process a task .md file for telemetry stamping.

    Returns list of actions taken (empty if no changes).
    """
    content = path.read_text(encoding="utf-8")
    original = content
    actions = []

    status = parse_metadata_field(content, "Status")
    started = parse_metadata_field(content, "Started")
    completed = parse_metadata_field(content, "Completed")

    # Status = "In Progress" + Started = sentinel → stamp Started
    if status and status.lower() == "in progress" and started == SENTINEL:
        content = replace_metadata_field(content, "Started", now)
        actions.append("Started")

    # Status = "Done" + Completed = sentinel → stamp Completed + Duration
    if status and status.lower() == "done" and completed == SENTINEL:
        cur_started = parse_metadata_field(content, "Started")
        if cur_started == SENTINEL:
            content = replace_metadata_field(content, "Started", now)
            cur_started = now
            actions.append("Started")

        content = replace_metadata_field(content, "Completed", now)
        actions.append("Completed")

        cur_duration = parse_metadata_field(content, "Duration")
        if cur_duration == SENTINEL:
            duration = format_duration(cur_started, now)
            content = replace_metadata_field(content, "Duration", duration)
            actions.append(f"Duration={duration}")

    if content != original:
        path.write_text(content, encoding="utf-8")

    return actions


def main() -> None:
    """Entry point: read hook JSON from stdin, process file, output result."""
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)

        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        if not file_path:
            return

        # Normalize to relative path for pattern matching
        path = Path(file_path)
        try:
            rel = str(path.relative_to(Path.cwd()))
        except ValueError:
            rel = str(path)

        now = now_stamp()
        actions: list[str] = []

        if BEAN_RE.search(rel):
            actions = handle_bean_file(path, now)
        elif TASK_RE.search(rel):
            actions = handle_task_file(path, now)

        if actions:
            stamped = ", ".join(actions)
            msg = (
                f"Telemetry: stamped {stamped} in {path.name} "
                f"(file auto-modified, re-read before next edit)"
            )
            print(json.dumps({"message": msg}))

    except Exception as e:
        print(f"telemetry-stamp: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()

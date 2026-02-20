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

# Fallback pricing if config file is missing or unparseable
DEFAULT_INPUT_RATE = 0.000015          # $15/MTok
DEFAULT_CACHE_CREATION_RATE = 0.00001875  # $18.75/MTok
DEFAULT_CACHE_READ_RATE = 0.0000015    # $1.50/MTok
DEFAULT_OUTPUT_RATE = 0.000075         # $75/MTok

# Patterns to match bean and task files (relative paths from repo root)
BEAN_RE = re.compile(r"ai/beans/BEAN-\d+-[^/]+/bean\.md$")
TASK_RE = re.compile(r"ai/beans/BEAN-\d+-[^/]+/tasks/.*\.md$")


def read_pricing() -> tuple[float, float, float, float]:
    """Read token pricing from ai/context/token-pricing.md.

    Returns (input_rate, cache_creation_rate, cache_read_rate, output_rate)
    in dollars per token. Falls back to defaults if the file is missing.
    """
    try:
        candidates = [
            Path.cwd() / "ai" / "context" / "token-pricing.md",
        ]
        script_dir = Path(__file__).resolve().parent
        repo_root = script_dir.parent.parent
        candidates.append(repo_root / "ai" / "context" / "token-pricing.md")

        content = None
        for path in candidates:
            if path.exists():
                content = path.read_text(encoding="utf-8")
                break

        if content is None:
            return (DEFAULT_INPUT_RATE, DEFAULT_CACHE_CREATION_RATE,
                    DEFAULT_CACHE_READ_RATE, DEFAULT_OUTPUT_RATE)

        input_rate = DEFAULT_INPUT_RATE
        cache_creation_rate = DEFAULT_CACHE_CREATION_RATE
        cache_read_rate = DEFAULT_CACHE_READ_RATE
        output_rate = DEFAULT_OUTPUT_RATE

        for line in content.splitlines():
            m = re.search(r"\$([0-9.]+)\s+per token", line)
            if not m:
                continue
            rate = float(m.group(1))
            if "**Input Rate**" in line:
                input_rate = rate
            elif "**Cache Creation Rate**" in line:
                cache_creation_rate = rate
            elif "**Cache Read Rate**" in line:
                cache_read_rate = rate
            elif "**Output Rate**" in line:
                output_rate = rate

        return input_rate, cache_creation_rate, cache_read_rate, output_rate

    except Exception:
        return (DEFAULT_INPUT_RATE, DEFAULT_CACHE_CREATION_RATE,
                DEFAULT_CACHE_READ_RATE, DEFAULT_OUTPUT_RATE)


def compute_cost(tokens_in: int, tokens_out: int,
                  cache_creation: int = 0, cache_read: int = 0) -> float:
    """Compute dollar cost from token counts using config rates.

    tokens_in is the combined total (non-cached + cache_creation + cache_read).
    Cache tokens are subtracted from tokens_in before applying the base input
    rate, then charged at their own tier rates.
    """
    input_rate, cache_creation_rate, cache_read_rate, output_rate = read_pricing()
    non_cached_in = max(0, tokens_in - cache_creation - cache_read)
    return (non_cached_in * input_rate
            + cache_creation * cache_creation_rate
            + cache_read * cache_read_rate
            + tokens_out * output_rate)


def format_cost(cost: float) -> str:
    """Format a dollar cost for display.

    Returns '$X.XX' for amounts >= $0.01, '< $0.01' for smaller amounts.
    """
    if cost < 0.01:
        return "< $0.01"
    return f"${cost:.2f}"


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


def add_metadata_field(content: str, field: str, value: str) -> str:
    """Add a new metadata field row to the first markdown table in content.

    Inserts | **Field** | value | after the last row of the first metadata table.
    Returns content unchanged if no table is found.
    """
    lines = content.splitlines()
    last_row_idx = -1
    separator_seen = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and re.match(r"^\|[\s\-|]+\|$", stripped):
            separator_seen = True
            continue
        if separator_seen and stripped.startswith("|"):
            last_row_idx = i
        elif separator_seen and not stripped.startswith("|"):
            break

    if last_row_idx < 0:
        return content

    new_row = f"| **{field}** | {value} |"
    lines.insert(last_row_idx + 1, new_row)
    return "\n".join(lines)


def ensure_metadata_field(content: str, field: str, default: str = SENTINEL) -> str:
    """Ensure a metadata field exists, adding it if missing.

    Returns content unchanged if the field already exists.
    """
    if parse_metadata_field(content, field) is not None:
        return content
    return add_metadata_field(content, field, default)


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


def parse_duration_to_seconds(dur: str) -> int | None:
    """Parse a duration string like '< 1m', '5m', '1h 30m' to seconds."""
    dur = dur.strip()
    if dur == "< 1m":
        return 30  # approximate
    m = re.match(r"^(?:(\d+)h)?\s*(?:(\d+)m)?$", dur)
    if m and (m.group(1) or m.group(2)):
        hours = int(m.group(1) or 0)
        minutes = int(m.group(2) or 0)
        return hours * 3600 + minutes * 60
    return None


def parse_tasks_table(content: str) -> list[tuple[str, str, str]]:
    """Parse the Tasks table in a bean.md.

    Returns list of (num, task_name, owner) for rows with non-empty task names.
    """
    rows: list[tuple[str, str, str]] = []
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
        if len(cells) >= 3 and cells[1]:
            rows.append((cells[0], cells[1], cells[2]))
    return rows


def find_telemetry_table(content: str) -> tuple[int, int, list[str]]:
    """Find the per-task Telemetry table in a bean.md.

    Returns (first_data_line_idx, last_data_line_idx+1, data_row_lines).
    Returns (-1, -1, []) if not found.
    """
    lines = content.splitlines()
    in_telemetry = False
    separator_idx = -1
    data_rows: list[tuple[int, str]] = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## Telemetry"):
            in_telemetry = True
            continue
        if in_telemetry and stripped.startswith("##"):
            break
        if not in_telemetry:
            continue
        # Identify the per-task header (has "Duration" — the summary table has "Metric")
        if stripped.startswith("|") and "Duration" in stripped and "Task" in stripped:
            continue
        if separator_idx < 0 and re.match(r"^\|[\s\-|]+\|$", stripped):
            separator_idx = i
            continue
        if separator_idx >= 0 and stripped.startswith("|"):
            # Stop at the summary table (has "Metric" or bold fields)
            if "**" in stripped or "Metric" in stripped:
                break
            data_rows.append((i, stripped))
        elif separator_idx >= 0 and not stripped.startswith("|"):
            if stripped:
                break

    if separator_idx < 0:
        return -1, -1, []

    if not data_rows:
        return separator_idx + 1, separator_idx + 1, []

    return data_rows[0][0], data_rows[-1][0] + 1, [row for _, row in data_rows]


def telemetry_row_nums(rows: list[str]) -> set[str]:
    """Extract task numbers from telemetry table rows."""
    nums: set[str] = set()
    for row in rows:
        cells = [c.strip() for c in row.split("|")]
        cells = [c for c in cells if c]
        if cells and cells[0] and cells[0] not in ("", SENTINEL):
            nums.add(cells[0])
    return nums


def is_empty_template_row(row: str) -> bool:
    """Check if a telemetry row is the empty template row."""
    cells = [c.strip() for c in row.split("|")]
    cells = [c for c in cells if c]
    return all(not c or c == SENTINEL for c in cells[1:])


def sync_telemetry_table(content: str) -> tuple[str, list[str]]:
    """Sync the Telemetry per-task table with the Tasks table.

    Adds rows for tasks not yet in the Telemetry table.
    Returns (new_content, actions_taken).
    """
    tasks = parse_tasks_table(content)
    if not tasks:
        return content, []

    lines = content.splitlines()
    first_data, end_data, existing_rows = find_telemetry_table(content)
    if first_data < 0:
        return content, []

    # If only an empty template row exists, treat it as no existing data
    has_only_template = (
        len(existing_rows) == 1 and is_empty_template_row(existing_rows[0])
    )
    existing_nums = set() if has_only_template else telemetry_row_nums(existing_rows)

    new_rows: list[str] = []
    actions: list[str] = []
    for num, name, owner in tasks:
        if num not in existing_nums:
            row = (
                f"| {num} | {name} | {owner}"
                f" | {SENTINEL} | {SENTINEL} | {SENTINEL} | {SENTINEL} |"
            )
            new_rows.append(row)
            actions.append(f"Telem row {num}")

    if not new_rows:
        return content, []

    if has_only_template:
        # Replace the empty template row with real data
        lines[first_data:end_data] = new_rows
    else:
        # Append after existing rows
        for idx, row in enumerate(new_rows):
            lines.insert(end_data + idx, row)

    return "\n".join(lines), actions


def update_telemetry_row_duration(
    content: str, task_num: str, duration: str,
) -> tuple[str, bool]:
    """Update the Duration column of a specific telemetry row.

    Returns (new_content, changed).
    """
    lines = content.splitlines()
    in_telemetry = False
    separator_seen = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## Telemetry"):
            in_telemetry = True
            continue
        if in_telemetry and stripped.startswith("##"):
            break
        if not in_telemetry:
            continue
        if re.match(r"^\|[\s\-|]+\|$", stripped):
            separator_seen = True
            continue
        if not separator_seen or not stripped.startswith("|"):
            continue
        if "**" in stripped or "Metric" in stripped:
            break

        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c]
        if cells and cells[0] == task_num and len(cells) >= 4:
            if cells[3] == SENTINEL:
                cells[3] = duration
                lines[i] = "| " + " | ".join(cells) + " |"
                return "\n".join(lines), True

    return content, False


def sum_telemetry_durations(content: str) -> str | None:
    """Sum per-task durations from the Telemetry table."""
    _, _, rows = find_telemetry_table(content)
    total_seconds = 0
    found_any = False

    for row in rows:
        cells = [c.strip() for c in row.split("|")]
        cells = [c for c in cells if c]
        if len(cells) >= 4:
            dur = cells[3]
            if dur and dur != SENTINEL:
                secs = parse_duration_to_seconds(dur)
                if secs is not None:
                    total_seconds += secs
                    found_any = True

    if not found_any:
        return None
    return format_seconds(total_seconds)


def extract_task_number(filename: str) -> str | None:
    """Extract task number from a task filename like '01-developer-slug.md'."""
    m = re.match(r"^(\d+)-", filename)
    if m:
        return str(int(m.group(1)))
    return None


def find_git_toplevel() -> Path | None:
    """Find the git top-level directory (handles worktrees).

    In a worktree, git rev-parse --show-toplevel returns the worktree root.
    git rev-parse --git-common-dir returns the path to the shared .git dir,
    which is inside the main repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            git_common = Path(result.stdout.strip())
            if not git_common.is_absolute():
                git_common = (Path.cwd() / git_common).resolve()
            # .git dir is usually at <repo>/.git
            return git_common.parent
    except Exception:
        pass
    return None


def find_session_jsonl() -> Path | None:
    """Find the JSONL conversation file for the current Claude Code session.

    Looks in ~/.claude/projects/<project-hash>/ for the most recently
    modified .jsonl file (excluding subagents/).
    Handles git worktrees by also checking the main repo's project hash.
    Returns the path, or None if not found.
    """
    try:
        claude_dir = Path.home() / ".claude" / "projects"
        if not claude_dir.exists():
            return None

        # Build candidate project directory paths
        candidate_dirs: list[Path] = []

        # 1. Current working directory hash
        cwd_hash = str(Path.cwd()).replace("/", "-")
        if not cwd_hash.startswith("-"):
            cwd_hash = "-" + cwd_hash
        candidate_dirs.append(claude_dir / cwd_hash)

        # 2. Git main repo hash (for worktree support)
        main_repo = find_git_toplevel()
        if main_repo and main_repo != Path.cwd():
            repo_hash = str(main_repo).replace("/", "-")
            if not repo_hash.startswith("-"):
                repo_hash = "-" + repo_hash
            candidate_dirs.append(claude_dir / repo_hash)

        # Try each candidate directory
        for project_dir in candidate_dirs:
            if not project_dir.exists():
                continue
            jsonl_files = [
                f for f in project_dir.iterdir()
                if f.is_file() and f.suffix == ".jsonl"
            ]
            if jsonl_files:
                return max(jsonl_files, key=lambda f: f.stat().st_mtime)

        # Fallback: use the most recently modified project dir
        candidates = []
        for d in claude_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                candidates.append(d)
        if not candidates:
            return None
        project_dir = max(candidates, key=lambda d: d.stat().st_mtime)

        jsonl_files = [
            f for f in project_dir.iterdir()
            if f.is_file() and f.suffix == ".jsonl"
        ]
        if not jsonl_files:
            return None

        return max(jsonl_files, key=lambda f: f.stat().st_mtime)

    except Exception as e:
        print(f"telemetry-stamp: session JSONL search failed: {e}",
              file=sys.stderr)
        return None


def sum_session_tokens(jsonl_path: Path) -> tuple[int, int, int, int]:
    """Sum cumulative tokens from a JSONL conversation file.

    Parses all assistant messages and sums token usage across all tiers:
    - input_tokens: non-cached input
    - cache_creation_input_tokens: tokens written to prompt cache
    - cache_read_input_tokens: tokens read from prompt cache
    - output_tokens: output

    Returns (total_input, total_output, total_cache_creation, total_cache_read).
    Total input includes all three input tiers (input + cache_creation + cache_read).
    """
    total_in = 0
    total_out = 0
    total_cache_creation = 0
    total_cache_read = 0
    try:
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") != "assistant":
                    continue
                usage = msg.get("message", {}).get("usage", {})
                total_in += usage.get("input_tokens", 0)
                total_cache_creation += usage.get(
                    "cache_creation_input_tokens", 0)
                total_cache_read += usage.get(
                    "cache_read_input_tokens", 0)
                total_out += usage.get("output_tokens", 0)
    except Exception:
        pass
    # Total input = all three input tiers combined
    combined_in = total_in + total_cache_creation + total_cache_read
    return combined_in, total_out, total_cache_creation, total_cache_read


def watermark_path(bean_dir: Path) -> Path:
    """Return the path to the .telemetry.json watermark file."""
    return bean_dir / ".telemetry.json"


def save_watermark(
    bean_dir: Path, task_num: str, tokens_in: int, tokens_out: int,
    cache_creation: int = 0, cache_read: int = 0,
) -> None:
    """Save a token watermark for a task start."""
    wm_path = watermark_path(bean_dir)
    data: dict = {}
    if wm_path.exists():
        try:
            data = json.loads(wm_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    data[f"task_{task_num}_start_in"] = tokens_in
    data[f"task_{task_num}_start_out"] = tokens_out
    data[f"task_{task_num}_start_cc"] = cache_creation
    data[f"task_{task_num}_start_cr"] = cache_read
    wm_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_watermark(
    bean_dir: Path, task_num: str,
) -> tuple[int, int, int, int] | None:
    """Load a token watermark for a task.

    Returns (start_tokens_in, start_tokens_out, cache_creation, cache_read)
    or None if not found. Old watermarks without cache fields default to 0.
    """
    wm_path = watermark_path(bean_dir)
    if not wm_path.exists():
        return None
    try:
        data = json.loads(wm_path.read_text(encoding="utf-8"))
        key_in = f"task_{task_num}_start_in"
        key_out = f"task_{task_num}_start_out"
        if key_in in data and key_out in data:
            return (
                data[key_in], data[key_out],
                data.get(f"task_{task_num}_start_cc", 0),
                data.get(f"task_{task_num}_start_cr", 0),
            )
    except (json.JSONDecodeError, OSError):
        pass
    return None


def format_tokens(count: int) -> str:
    """Format a token count with comma separators."""
    return f"{count:,}"


def update_telemetry_row_tokens(
    content: str, task_num: str, tokens_in: str, tokens_out: str,
    cache_creation: int = 0, cache_read: int = 0,
) -> tuple[str, bool]:
    """Update Tokens In, Tokens Out, and Cost columns of a telemetry row.

    Returns (new_content, changed).
    """
    lines = content.splitlines()
    in_telemetry = False
    separator_seen = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## Telemetry"):
            in_telemetry = True
            continue
        if in_telemetry and stripped.startswith("##"):
            break
        if not in_telemetry:
            continue
        if re.match(r"^\|[\s\-|]+\|$", stripped):
            separator_seen = True
            continue
        if not separator_seen or not stripped.startswith("|"):
            continue
        if "**" in stripped or "Metric" in stripped:
            break

        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c]
        if cells and cells[0] == task_num and len(cells) >= 6:
            changed = False
            if cells[4] == SENTINEL:
                cells[4] = tokens_in
                changed = True
            if cells[5] == SENTINEL:
                cells[5] = tokens_out
                changed = True
            # Compute and write Cost column (index 6) if tokens were written
            if changed:
                try:
                    tin = int(tokens_in.replace(",", ""))
                    tout = int(tokens_out.replace(",", ""))
                    cost = compute_cost(tin, tout, cache_creation, cache_read)
                    cost_str = format_cost(cost)
                except (ValueError, TypeError):
                    cost_str = SENTINEL
                # Ensure row has 7 columns (add Cost if missing)
                while len(cells) < 7:
                    cells.append(SENTINEL)
                if cells[6] == SENTINEL:
                    cells[6] = cost_str
                lines[i] = "| " + " | ".join(cells) + " |"
                return "\n".join(lines), True

    return content, False


def sum_telemetry_tokens(content: str) -> tuple[str | None, str | None]:
    """Sum per-task token values from the Telemetry table.

    Returns (total_in_str, total_out_str) or (None, None) if no data.
    """
    _, _, rows = find_telemetry_table(content)
    total_in = 0
    total_out = 0
    found_any = False

    for row in rows:
        cells = [c.strip() for c in row.split("|")]
        cells = [c for c in cells if c]
        if len(cells) >= 6:
            tok_in = cells[4].replace(",", "")
            tok_out = cells[5].replace(",", "")
            if tok_in and tok_in != SENTINEL:
                try:
                    total_in += int(tok_in)
                    found_any = True
                except ValueError:
                    pass
            if tok_out and tok_out != SENTINEL:
                try:
                    total_out += int(tok_out)
                    found_any = True
                except ValueError:
                    pass

    if not found_any:
        return None, None
    return format_tokens(total_in), format_tokens(total_out)


def sum_telemetry_costs(content: str) -> str | None:
    """Sum per-task cost values from the Telemetry table.

    Returns formatted total cost string, or None if no cost data.
    """
    _, _, rows = find_telemetry_table(content)
    total_cost = 0.0
    found_any = False

    for row in rows:
        cells = [c.strip() for c in row.split("|")]
        cells = [c for c in cells if c]
        if len(cells) >= 7:
            cost_str = cells[6]
            if cost_str and cost_str != SENTINEL and cost_str != "< $0.01":
                # Parse "$X.XX" format
                m = re.match(r"^\$([0-9.]+)$", cost_str)
                if m:
                    total_cost += float(m.group(1))
                    found_any = True
            elif cost_str == "< $0.01":
                # Count as ~$0.005
                total_cost += 0.005
                found_any = True

    if not found_any:
        # Fall back: compute from token totals if available
        tok_in_str, tok_out_str = sum_telemetry_tokens(content)
        if tok_in_str and tok_out_str:
            try:
                tin = int(tok_in_str.replace(",", ""))
                tout = int(tok_out_str.replace(",", ""))
                total_cost = compute_cost(tin, tout)
                found_any = True
            except (ValueError, TypeError):
                pass

    if not found_any:
        return None
    return format_cost(total_cost)


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


def needs_stamp(value: str | None) -> bool:
    """Check if a metadata field needs stamping.

    Returns True if the value is the sentinel em-dash, None (missing), or
    a date-only string missing the time component.
    """
    if value is None or value == SENTINEL:
        return True
    # Date-only format like "2026-02-16" — missing HH:MM
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value.strip()):
        return True
    return False


def handle_bean_file(path: Path, now: str) -> list[str]:
    """Process a bean.md file for telemetry stamping.

    Returns list of actions taken (empty if no changes).
    """
    content = path.read_text(encoding="utf-8")
    original = content
    actions = []

    # Ensure telemetry fields exist in the metadata table
    for field in ("Started", "Completed", "Duration"):
        content = ensure_metadata_field(content, field)

    status = parse_metadata_field(content, "Status")
    started = parse_metadata_field(content, "Started")
    completed = parse_metadata_field(content, "Completed")

    # Status = "In Progress" + Started needs stamp → stamp Started
    if status and status.lower() == "in progress" and needs_stamp(started):
        content = replace_metadata_field(content, "Started", now)
        actions.append("Started")

    # Status = "Done" + Completed needs stamp → stamp Completed + Duration
    if status and status.lower() == "done" and needs_stamp(completed):
        # If Started also needs stamp, stamp it too
        cur_started = parse_metadata_field(content, "Started")
        if needs_stamp(cur_started):
            content = replace_metadata_field(content, "Started", now)
            cur_started = now
            actions.append("Started")

        content = replace_metadata_field(content, "Completed", now)
        actions.append("Completed")

        cur_duration = parse_metadata_field(content, "Duration")
        if needs_stamp(cur_duration):
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
            # Prefer sum of per-task durations; fall back to git; then
            # Started/Completed
            total_dur = sum_telemetry_durations(content)
            if not total_dur:
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

        # Fill Total Tokens In / Total Tokens Out
        total_tok_in_val = parse_metadata_field(content, "Total Tokens In")
        total_tok_out_val = parse_metadata_field(content, "Total Tokens Out")
        if total_tok_in_val == SENTINEL or total_tok_out_val == SENTINEL:
            tok_in_sum, tok_out_sum = sum_telemetry_tokens(content)
            if tok_in_sum and total_tok_in_val == SENTINEL:
                content = replace_metadata_field(
                    content, "Total Tokens In", tok_in_sum,
                )
                actions.append(f"Total Tokens In={tok_in_sum}")
            if tok_out_sum and total_tok_out_val == SENTINEL:
                content = replace_metadata_field(
                    content, "Total Tokens Out", tok_out_sum,
                )
                actions.append(f"Total Tokens Out={tok_out_sum}")

        # Fill Total Cost
        total_cost_val = parse_metadata_field(content, "Total Cost")
        if total_cost_val == SENTINEL:
            total_cost = sum_telemetry_costs(content)
            if total_cost:
                content = replace_metadata_field(
                    content, "Total Cost", total_cost,
                )
                actions.append(f"Total Cost={total_cost}")

    # Sync telemetry table with tasks table (add missing rows)
    content, sync_actions = sync_telemetry_table(content)
    actions.extend(sync_actions)

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

    # Ensure telemetry fields exist in the metadata table
    for field in ("Started", "Completed", "Duration"):
        content = ensure_metadata_field(content, field)

    status = parse_metadata_field(content, "Status")
    started = parse_metadata_field(content, "Started")
    completed = parse_metadata_field(content, "Completed")

    bean_dir = path.parent.parent  # ai/beans/BEAN-NNN-slug/
    task_num = extract_task_number(path.name)

    # Status = "In Progress" + Started needs stamp → stamp Started
    if status and status.lower() == "in progress" and needs_stamp(started):
        content = replace_metadata_field(content, "Started", now)
        actions.append("Started")

        # Record token watermark at task start
        if task_num:
            try:
                jsonl_path = find_session_jsonl()
                if jsonl_path:
                    tok_in, tok_out, cc, cr = sum_session_tokens(jsonl_path)
                    save_watermark(bean_dir, task_num, tok_in, tok_out,
                                   cc, cr)
                    actions.append(f"Watermark task {task_num}")
                else:
                    print(
                        f"telemetry-stamp: no session JSONL found for watermark"
                        f" (cwd={Path.cwd()})",
                        file=sys.stderr,
                    )
            except Exception as e:
                print(
                    f"telemetry-stamp: watermark save failed: {e}",
                    file=sys.stderr,
                )

    # Status = "Done" + Completed needs stamp → stamp Completed + Duration
    if status and status.lower() == "done" and needs_stamp(completed):
        cur_started = parse_metadata_field(content, "Started")
        if needs_stamp(cur_started):
            content = replace_metadata_field(content, "Started", now)
            cur_started = now
            actions.append("Started")

        content = replace_metadata_field(content, "Completed", now)
        actions.append("Completed")

        cur_duration = parse_metadata_field(content, "Duration")
        if needs_stamp(cur_duration):
            duration = format_duration(cur_started, now)
            content = replace_metadata_field(content, "Duration", duration)
            actions.append(f"Duration={duration}")

        # Propagate per-task duration and tokens to bean.md telemetry table
        if task_num:
            final_dur = parse_metadata_field(content, "Duration")
            bean_path = bean_dir / "bean.md"

            # Compute token delta from watermark
            tok_in_str = None
            tok_out_str = None
            delta_cc = 0
            delta_cr = 0
            try:
                jsonl_path = find_session_jsonl()
                if jsonl_path:
                    wm = load_watermark(bean_dir, task_num)
                    cur_in, cur_out, cur_cc, cur_cr = sum_session_tokens(
                        jsonl_path)
                    if wm:
                        start_in, start_out, start_cc, start_cr = wm
                        delta_in = max(0, cur_in - start_in)
                        delta_out = max(0, cur_out - start_out)
                        delta_cc = max(0, cur_cc - start_cc)
                        delta_cr = max(0, cur_cr - start_cr)
                    else:
                        # No watermark — use full session tokens as fallback
                        delta_in = cur_in
                        delta_out = cur_out
                        delta_cc = cur_cc
                        delta_cr = cur_cr
                    tok_in_str = format_tokens(delta_in)
                    tok_out_str = format_tokens(delta_out)
                else:
                    print(
                        f"telemetry-stamp: no session JSONL found for token"
                        f" delta (cwd={Path.cwd()})",
                        file=sys.stderr,
                    )
            except Exception as e:
                print(
                    f"telemetry-stamp: token delta failed: {e}",
                    file=sys.stderr,
                )

            if bean_path.exists():
                try:
                    bean_content = bean_path.read_text(encoding="utf-8")
                    changed_any = False

                    if final_dur and final_dur != SENTINEL:
                        bean_content, changed = update_telemetry_row_duration(
                            bean_content, task_num, final_dur,
                        )
                        if changed:
                            changed_any = True
                            actions.append(f"Bean telem row {task_num}")

                    if tok_in_str and tok_out_str:
                        bean_content, changed = update_telemetry_row_tokens(
                            bean_content, task_num, tok_in_str, tok_out_str,
                            delta_cc, delta_cr,
                        )
                        if changed:
                            changed_any = True
                            actions.append(
                                f"Tokens task {task_num}: "
                                f"in={tok_in_str} out={tok_out_str}"
                            )

                    if changed_any:
                        bean_path.write_text(bean_content, encoding="utf-8")
                except Exception as e:
                    print(
                        f"telemetry-stamp: bean telemetry update failed: {e}",
                        file=sys.stderr,
                    )

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

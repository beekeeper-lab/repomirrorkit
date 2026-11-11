"""Start/stop an application under test (original or rebuild).

The app is launched with a shell command (default ``bash start.sh``) in its
directory; it must serve HTTP on the port given in ``$PORT`` and stay in the
foreground. The process group is terminated on exit so no server is leaked.
"""

from __future__ import annotations

import os
import shlex
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path
from types import TracebackType
from typing import IO

import structlog

logger = structlog.get_logger()

DEFAULT_START_COMMAND = "bash start.sh"
STARTUP_TIMEOUT_SECONDS = 120.0


class AppStartError(Exception):
    """The application under test did not come up."""


def free_port() -> int:
    """An unused localhost TCP port."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


def _tcp_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


class AppProcess:
    """Context manager running an app and exposing its ``base_url``.

    Args:
        app_dir: directory containing the app.
        command: shell command that starts it (reads ``$PORT``).
        env: extra environment variables (e.g. ``{"API_KEY": "demo-key"}``).
        startup_timeout: seconds to wait for the port to accept connections.
    """

    def __init__(
        self,
        app_dir: Path,
        command: str = DEFAULT_START_COMMAND,
        env: dict[str, str] | None = None,
        startup_timeout: float = STARTUP_TIMEOUT_SECONDS,
    ) -> None:
        self.app_dir = Path(app_dir)
        self.command = command
        self.env = env or {}
        self.startup_timeout = startup_timeout
        self.port = 0
        self._proc: subprocess.Popen[bytes] | None = None
        self._log: deque[str] = deque(maxlen=60)
        self._log_file: IO[bytes] | None = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def log_tail(self) -> str:
        if self._log_file is not None:
            self._log_file.flush()
        try:
            return self._read_log()
        except OSError:
            return ""

    def _read_log(self) -> str:
        path = self.app_dir / ".parity-app.log"
        if not path.is_file():
            return ""
        return "\n".join(path.read_text(errors="replace").splitlines()[-40:])

    def __enter__(self) -> AppProcess:
        self.port = free_port()
        env = {
            **os.environ,
            **self.env,
            "PORT": str(self.port),
            "PYTHONUNBUFFERED": "1",
        }
        self._log_file = (self.app_dir / ".parity-app.log").open("wb")
        self._proc = subprocess.Popen(  # noqa: S603 - command is operator-supplied
            shlex.split(self.command),
            cwd=str(self.app_dir),
            env=env,
            stdout=self._log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                raise AppStartError(
                    f"app exited with code {self._proc.returncode} before serving:\n{self.log_tail}"
                )
            if _tcp_open(self.port):
                logger.info("parity_app_up", port=self.port, cmd=self.command)
                return self
            time.sleep(0.25)
        self.__exit__(None, None, None)
        raise AppStartError(
            f"app did not accept connections on port {self.port} within "
            f"{self.startup_timeout:.0f}s:\n{self.log_tail}"
        )

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        proc = self._proc
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None


def http_call(
    base_url: str,
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
    json_body: object | None = None,
    timeout: float = 15.0,
) -> tuple[int, object | None, str]:
    """One HTTP request → ``(status, parsed_json_or_None, raw_text)``."""
    import json

    data: bytes | None = None
    hdrs = dict(headers or {})
    if json_body is not None:
        data = json.dumps(json_body).encode()
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(  # noqa: S310 - scheme fixed to http://127.0.0.1
        base_url + path, data=data, method=method.upper(), headers=hdrs
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            status = resp.status
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as err:
        status = err.code
        raw = err.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        return 0, None, f"transport error: {exc}"
    try:
        parsed: object | None = json.loads(raw) if raw.strip() else None
    except json.JSONDecodeError:
        parsed = None
    return status, parsed, raw
